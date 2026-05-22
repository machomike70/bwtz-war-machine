from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging
from datetime import datetime, date
from contextlib import asynccontextmanager

import tweepy
from tweepy.errors import TweepyException, TooManyRequests, Unauthorized, Forbidden
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

# ----------------------------- Logging -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] x-twitter-bot: %(message)s"
)
logger = logging.getLogger("x-twitter-bot")

# ----------------------------- Config (ENV ONLY - NEVER HARDCODE) -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_stack:change-me@postgres:5432/ai_stack")

X_API_KEY = os.getenv("X_API_KEY", "")
X_API_KEY_SECRET = os.getenv("X_API_KEY_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")

# Global creds for current phase (per-account / white-label in future via accounts table + token vault)
X_CREDS_CONFIGURED = all([X_API_KEY, X_API_KEY_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET])

# ----------------------------- DB Helpers -----------------------------
def get_db():
    """Sync psycopg connection (matches orchestrator/worker pattern)."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def init_queue_table():
    """Ensure x_post_queue exists (idempotent; worker also creates on its start)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS x_post_queue (
                        id SERIAL PRIMARY KEY,
                        account_handle TEXT NOT NULL,
                        content TEXT NOT NULL,
                        status TEXT DEFAULT 'queued',
                        previewed BOOLEAN DEFAULT FALSE,
                        tweet_id TEXT,
                        post_url TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
        logger.info("x_post_queue table ensured")
    except Exception as e:
        logger.warning(f"Could not init queue table (DB may be unavailable yet): {e}")


# ----------------------------- X API v2 Client (tweepy, OAuth 1.0a User Context) -----------------------------
class XPoster:
    """
    Safe X Posting wrapper.
    - Loads creds ONLY from environment.
    - Every real post requires explicit /confirm after /preview + /queue.
    - Supports dry-run preview + rate limit awareness + duplicate safety.
    - Future: per-account token lookup from DB.
    """

    def __init__(self):
        self.creds_configured = X_CREDS_CONFIGURED
        self.client: Optional[tweepy.Client] = None
        if self.creds_configured:
            try:
                self.client = tweepy.Client(
                    consumer_key=X_API_KEY,
                    consumer_secret=X_API_KEY_SECRET,
                    access_token=X_ACCESS_TOKEN,
                    access_token_secret=X_ACCESS_TOKEN_SECRET,
                    wait_on_rate_limit=False,  # We handle explicitly for human confirmation flow
                )
                logger.info("Tweepy X Client initialized with user context (OAuth1a)")
            except Exception as e:
                logger.error(f"Failed to init tweepy client: {e}")
                self.creds_configured = False
        else:
            logger.warning("X credentials NOT fully configured in env (X_API_*). All posting will be dry-run only.")

    def _get_username(self) -> str:
        """Best-effort username for URLs (cached simple)."""
        # In production we would cache /2/users/me on init
        return os.getenv("X_POSTING_USERNAME", "yourhandle")

    def validate_content(self, content: str) -> Dict[str, Any]:
        length = len(content)
        valid = 0 < length <= 280
        return {
            "length": length,
            "valid": valid,
            "warning": None if valid else f"Content length {length} exceeds 280 char X limit."
        }

    def check_duplicate_today(self, account_handle: str, content: str) -> Optional[str]:
        """Prevent obvious spam: check daily_posts for same content on same account today."""
        today = date.today()
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, status FROM daily_posts
                        WHERE account_handle = %s AND scheduled_for = %s AND content = %s
                        LIMIT 1
                        """,
                        (account_handle, today, content)
                    )
                    row = cur.fetchone()
                    if row:
                        return f"Duplicate detected in daily_posts (id={row['id']}, status={row['status']}). Already handled today."
        except Exception as e:
            logger.debug(f"Duplicate check skipped (DB issue): {e}")
        return None

    def preview(self, account_handle: str, content: str) -> Dict[str, Any]:
        """Dry-run: never posts. Returns exactly what would happen + safety info."""
        logger.info(f"PREVIEW requested for @{account_handle} (length={len(content)})")
        validation = self.validate_content(content)
        duplicate = self.check_duplicate_today(account_handle, content)

        rate_info = {
            "note": "Rate limit check is best-effort. Real limits enforced by X API on confirm.",
            "posting_limit_hint": "X v2 user context typically ~200 tweets / 3h window (varies by access tier)",
            "configured": self.creds_configured,
        }

        would_post_url = f"https://x.com/{account_handle.lstrip('@')}/status/DRYRUN-{int(datetime.now().timestamp())}"

        result = {
            "dry_run": True,
            "account_handle": account_handle,
            "content": content,
            "length": validation["length"],
            "valid": validation["valid"],
            "would_post_url": would_post_url,
            "rate_limit_info": rate_info,
            "duplicate_warning": duplicate,
            "message": "Dry-run successful. No post was made. Review content, then queue + confirm to post for real.",
            "safety": "HUMAN-IN-THE-LOOP: Real posting requires explicit /post/confirm. No auto-posting ever.",
        }
        if not validation["valid"]:
            result["message"] = "Validation failed. " + (validation.get("warning") or "")
        if duplicate:
            result["message"] += " " + duplicate
        return result

    def post_now(self, content: str) -> Dict[str, Any]:
        """REAL post. Called ONLY from /post/confirm after human approval. Robust error handling."""
        if not self.creds_configured or self.client is None:
            raise HTTPException(status_code=503, detail="X credentials not configured. Set X_API_* env vars and restart.")

        logger.info(f"REAL POST ATTEMPT (length={len(content)} chars)")

        try:
            # The actual X API v2 call (OAuth1a user context posts as the authenticated account)
            response = self.client.create_tweet(text=content)
            tweet_id = str(response.data["id"])
            post_url = f"https://x.com/i/web/status/{tweet_id}"

            logger.info(f"Successfully posted tweet id={tweet_id}")

            return {
                "success": True,
                "tweet_id": tweet_id,
                "post_url": post_url,
                "text": content[:100] + ("..." if len(content) > 100 else ""),
            }
        except TooManyRequests as e:
            # Rate limit - return actionable info
            retry_after = getattr(e, 'response', None)
            headers = {}
            if retry_after and hasattr(retry_after, 'headers'):
                headers = dict(retry_after.headers)
            logger.warning(f"Rate limited by X: {e}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "X rate limit exceeded",
                    "message": "Too many requests. Wait and try again later.",
                    "retry_after": headers.get("x-rate-limit-reset", "unknown"),
                    "headers": headers,
                }
            )
        except (Unauthorized, Forbidden) as e:
            logger.error(f"Auth/permission error posting to X: {e}")
            raise HTTPException(status_code=401, detail=f"X auth error: {str(e)}. Check tokens have write permissions.")
        except TweepyException as e:
            logger.error(f"Tweepy error during post: {e}")
            raise HTTPException(status_code=502, detail=f"X API error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during real X post")
            raise HTTPException(status_code=500, detail=f"Unexpected posting error: {str(e)}")


# Global poster instance
x_poster = XPoster()


# ----------------------------- FastAPI App + Lifespan -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure DB table + log config status."""
    init_queue_table()
    if X_CREDS_CONFIGURED:
        logger.info("X posting engine READY (credentials loaded from env). Human confirmation required for every post.")
    else:
        logger.warning("X posting engine in DRY-RUN ONLY mode (missing X_API_* env vars).")
    yield
    logger.info("x-twitter-bot shutting down")


app = FastAPI(
    title="Bwtz War Machine - X Posting Engine",
    description="Safe human-in-the-loop X posting for Bear Witness $BWTZ | Xtreme Ripple Protocol",
    version="1.0.0",
    lifespan=lifespan,
)

# ----------------------------- Pydantic Models for Endpoints -----------------------------
class PostPreviewRequest(BaseModel):
    account_handle: str
    content: str


class PostQueueRequest(BaseModel):
    account_handle: str
    content: str


class PostConfirmRequest(BaseModel):
    queue_id: int


class QueueItem(BaseModel):
    id: int
    account_handle: str
    content: str
    status: str
    previewed: bool
    tweet_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


# ----------------------------- Core Endpoints (as specified) -----------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "x-twitter-bot",
        "company": "XtremeRippleProtocol LLC",
        "white_label_service": True,
        "phase": "1-2",
        "safety_model": "HUMAN-IN-THE-LOOP MANDATORY",
        "description": "Safe X posting engine. Every real post requires preview -> queue -> explicit confirm.",
        "x_credentials_configured": X_CREDS_CONFIGURED,
        "note": "Use /pricing for legacy tiers. Real posting is via safe /post/* endpoints."
    }


@app.get("/healthz")
def health():
    return {
        "ok": True,
        "service": "x-twitter-bot",
        "x_configured": X_CREDS_CONFIGURED,
        "queue_table": "ready"
    }


@app.post("/post/preview")
def post_preview(req: PostPreviewRequest):
    """POST /post/preview — dry-run, show what would be posted, rate limit check (simulated), duplicate warning."""
    if not req.content or not req.account_handle:
        raise HTTPException(400, "account_handle and content required")
    result = x_poster.preview(req.account_handle, req.content)
    logger.info(f"Preview response for {req.account_handle}: valid={result['valid']}")
    return result


@app.post("/post/queue")
def post_queue(req: PostQueueRequest):
    """POST /post/queue — add to internal queue (persisted in Postgres x_post_queue). Returns queue_id for later confirm."""
    if not req.content or not req.account_handle:
        raise HTTPException(400, "account_handle and content required")

    # Optional: run a preview internally and mark previewed
    preview_res = x_poster.preview(req.account_handle, req.content)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO x_post_queue (account_handle, content, status, previewed)
                    VALUES (%s, %s, 'queued', TRUE)
                    RETURNING id, created_at
                    """,
                    (req.account_handle, req.content)
                )
                row = cur.fetchone()
                queue_id = row["id"]
                created = row["created_at"].isoformat() if row["created_at"] else None

        logger.info(f"Queued post id={queue_id} for {req.account_handle}")
        return {
            "status": "queued",
            "queue_id": queue_id,
            "account_handle": req.account_handle,
            "created_at": created,
            "preview": preview_res,
            "message": "Post added to queue. Call /post/confirm with this queue_id to execute the real post (human confirmation required).",
            "next": "Use dashboard 'Confirm & Post' or POST /post/confirm"
        }
    except Exception as e:
        logger.error(f"Queue insert failed: {e}")
        raise HTTPException(500, f"Failed to queue: {str(e)}")


@app.get("/post/queue")
def get_post_queue(status: Optional[str] = None) -> List[QueueItem]:
    """GET /post/queue — list pending / queued posts."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        "SELECT * FROM x_post_queue WHERE status = %s ORDER BY created_at DESC LIMIT 50",
                        (status,)
                    )
                else:
                    cur.execute(
                        "SELECT * FROM x_post_queue WHERE status IN ('queued', 'confirmed') ORDER BY created_at DESC LIMIT 50"
                    )
                rows = cur.fetchall()

        items = []
        for r in rows:
            items.append(QueueItem(
                id=r["id"],
                account_handle=r["account_handle"],
                content=r["content"],
                status=r["status"],
                previewed=bool(r.get("previewed", False)),
                tweet_id=r.get("tweet_id"),
                post_url=r.get("post_url"),
                error_message=r.get("error_message"),
                created_at=r["created_at"].isoformat() if r.get("created_at") else ""
            ))
        return items
    except Exception as e:
        logger.error(f"Queue fetch error: {e}")
        raise HTTPException(500, str(e))


@app.post("/post/confirm")
def post_confirm(req: PostConfirmRequest):
    """
    POST /post/confirm — THE ONLY place real posts happen.
    Requires prior queue entry. Human must explicitly call this (via dashboard button).
    Updates queue status + attempts real X post with full error handling + backoff info.
    """
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM x_post_queue WHERE id = %s", (req.queue_id,))
                item = cur.fetchone()

                if not item:
                    raise HTTPException(404, f"Queue item {req.queue_id} not found")

                if item["status"] == "posted":
                    return {
                        "status": "already_posted",
                        "queue_id": req.queue_id,
                        "post_url": item.get("post_url"),
                        "message": "This item was already successfully posted."
                    }
                if item["status"] == "failed":
                    # allow retry on confirm? for now permit
                    pass

                account = item["account_handle"]
                content = item["content"]

                # Real post (only here!)
                try:
                    post_result = x_poster.post_now(content)
                except HTTPException as post_exc:
                    # Update queue with failure
                    cur.execute(
                        """
                        UPDATE x_post_queue
                        SET status = 'failed', error_message = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (str(post_exc.detail), req.queue_id)
                    )
                    raise  # re-raise to client

                # Success: update queue
                cur.execute(
                    """
                    UPDATE x_post_queue
                    SET status = 'posted',
                        tweet_id = %s,
                        post_url = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (post_result["tweet_id"], post_result["post_url"], req.queue_id)
                )

                # Bonus: try to mark matching daily_post as posted (best effort, non-fatal)
                try:
                    today = date.today()
                    cur.execute(
                        """
                        UPDATE daily_posts
                        SET status = 'posted', posted_at = NOW(), notes = %s
                        WHERE account_handle = %s AND scheduled_for = %s AND content = %s
                        """,
                        (f"Posted via x-twitter-bot queue_id={req.queue_id}", account, today, content)
                    )
                except Exception:
                    pass  # ignore if no match

        logger.info(f"CONFIRMED & POSTED queue_id={req.queue_id} -> tweet {post_result['tweet_id']}")
        return {
            "status": "posted",
            "queue_id": req.queue_id,
            "account_handle": account,
            "tweet_id": post_result["tweet_id"],
            "post_url": post_result["post_url"],
            "message": "Successfully posted to X. Human confirmation completed the action.",
            "safety_note": "This was the only code path that can create real tweets."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Confirm failed for queue {req.queue_id}")
        raise HTTPException(500, f"Confirm error: {str(e)}")


# ----------------------------- Status / Diagnostics -----------------------------
@app.get("/status")
def status():
    """Operational status for monitoring / dashboard."""
    return {
        "service": "x-twitter-bot",
        "x_credentials_loaded": X_CREDS_CONFIGURED,
        "tweepy_ready": x_poster.client is not None,
        "safety": "Every real post MUST go through explicit /post/confirm after preview+queue",
        "env_vars_required": ["X_API_KEY", "X_API_KEY_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"],
        "note": "Per-account credentials supported in future white-label releases via DB lookup."
    }


# Keep legacy /pricing and /orchestrate for compatibility
class OrchestrateRequest(BaseModel):
    task: str
    account: Optional[str] = None
    context: Optional[str] = None
    client_brand: Optional[str] = None
    plan: Optional[str] = "Free"


@app.post("/orchestrate")
def orchestrate(req: OrchestrateRequest):
    return {
        "status": "accepted",
        "service": "x-twitter-bot",
        "message": "Orchestration accepted. Use /post/preview + /post/queue + /post/confirm for safe posting.",
        "request": req.model_dump(),
    }


@app.get("/pricing")
def pricing():
    return {
        "service": "x-twitter-bot",
        "pricing_tiers": {
            "Free": {"posts_per_day": 5, "price_xrp": 0},
            "Basic": {"posts_per_day": "unlimited", "replies": True, "price_xrp": 6},
            "Pro": {"posts_per_day": "unlimited", "daily_batch": True, "white_label": True, "price_xrp": 12},
        }
    }


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "x-twitter-bot",
        "company": "XtremeRippleProtocol LLC",
        "white_label_service": True,
        "pricing": {
            "Free": "Limited to 5 posts/day",
            "Basic": "6 XRP per month - Unlimited posts & replies",
            "Pro": "12 XRP per month - Full features + daily batch generation"
        }
    }

class OrchestrateRequest(BaseModel):
    task: str
    account: Optional[str] = None
    context: Optional[str] = None
    client_brand: Optional[str] = None
    plan: Optional[str] = "Free"


@app.post("/orchestrate")
def orchestrate(req: OrchestrateRequest):
    """Future entrypoint for the growth bot orchestration (content gen + scheduling + posting)."""
    return {
        "status": "accepted",
        "service": "x-twitter-bot",
        "message": "Orchestration request received (stub - Phase 1 will implement real logic)",
        "request": req.model_dump(),
        "next_steps": "Scheduler + X API posting integration coming in Phase 1"
    }


@app.get("/healthz")
def health():
    return {"ok": True, "service": "x-twitter-bot"}


@app.get("/pricing")
def pricing():
    return {
        "service": "x-twitter-bot",
        "pricing_tiers": {
            "Free": {"posts_per_day": 5, "price_xrp": 0},
            "Basic": {"posts_per_day": "unlimited", "replies": True, "price_xrp": 6},
            "Pro": {"posts_per_day": "unlimited", "daily_batch": True, "white_label": True, "price_xrp": 12},
        }
    }


# ----------------------------- Phase 1+ X Posting Endpoints (stubs for contract testing) -----------------------------

class PostRequest(BaseModel):
    account: str
    content: str
    media_urls: list[str] | None = None
    dry_run: bool = True


@app.post("/post")
def post_to_x(req: PostRequest):
    """
    Basic X posting contract endpoint (stub).
    In real implementation this will use tweepy / X API v2 client with OAuth.
    For now returns accepted and simulates the call (dry_run supported).
    """
    # Placeholder for real X API call — tests will mock the underlying client
    if req.dry_run:
        return {
            "status": "accepted",
            "posted": False,
            "dry_run": True,
            "account": req.account,
            "message": "Dry-run: would have posted to X",
            "content_preview": req.content[:80] + ("..." if len(req.content) > 80 else ""),
        }
    return {
        "status": "accepted",
        "posted": True,
        "tweet_id": "mock_1234567890",
        "account": req.account,
        "message": "Posted to X (stub)",
    }
