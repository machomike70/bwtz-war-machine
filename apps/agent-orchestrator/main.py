"""
TextRp Daily Posts / X Growth Bot Orchestrator (Phase 1+)

- Serves the beautiful copy-to-clipboard daily dashboard at /
- Exposes /daily JSON (used by gateway proxy, worker scheduler, external clients)
- Prefers persisted posts from Postgres (written by the worker) when available for "today"
- Fallback to high-quality static templates (the original brand voices)
- Future: /generate, status updates, integration with x-twitter-bot for queuing
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import date
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

COMMUNITY_LINK = "https://x.com/i/communities/2027587775332290785"
CTA = f"\n\nJoin the TextRp community today 👇\n{COMMUNITY_LINK}"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_stack:change-me@postgres:5432/ai_stack")

app = FastAPI(title="TextRp Daily Posts", description="X Growth Bot Orchestrator for TextRP ecosystem")


# ----------------------------- DB helpers -----------------------------

def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def get_todays_posts_from_db() -> Dict[str, List[Dict[str, Any]]]:
    """Return today's posts grouped by account, preferring DB over templates."""
    today = date.today()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT account_handle, content, status, source
                    FROM daily_posts
                    WHERE scheduled_for = %s
                    ORDER BY account_handle, id
                    """,
                    (today,)
                )
                rows = cur.fetchall()

        if not rows:
            return {}

        grouped: Dict[str, List[Dict]] = {}
        for r in rows:
            h = r["account_handle"]
            if h not in grouped:
                grouped[h] = []
            grouped[h].append({
                "content": r["content"],
                "status": r["status"],
                "source": r["source"]
            })
        return grouped
    except Exception as e:
        # DB not ready or down → graceful fallback to static generation
        return {}


# ----------------------------- Static template generator (fallback) -----------------------------

def _base_posts_for_account(handle: str) -> List[str]:
    if handle == "@textrpsms":
        return [
            f"Good morning everyone. The TextRp community is a great place to connect, ask questions, and learn more about the platform.{CTA}",
            f"Platform update: TextRp Launch Packs are the keys to the kingdom — granting access to all current and future features, feature pack airdrops, rev share participation, and multipliers on all reward engines.{CTA}",
            f"Quick note: If you're new to TextRp, our community is open and welcoming. Feel free to join and connect with others who are building together.{CTA}",
            f"Evening check-in: Another solid day in the TextRp community. Lots of good conversations and support happening.{CTA}",
            f"Good night. The TextRp community remains a hub for onboarding and mutual support. Rest well — more updates coming soon.{CTA}",
        ]
    elif handle == "@bwtzbearwitness":
        return [
            f"Good morning. Another day of sharing the real story — redemption, survival, and building after 32 years inside. Art and life continue.{CTA}",
            f"From prison to freedom at 51. The chaos, the art, the redemption — this is my story being told day by day. BWTZ NFTs help build the tattoo shop and the life I love through art.{CTA}",
            f"Quick update from the real world: Life after release is wild. Grateful for every lesson and every new beginning.{CTA}",
            f"Love the support and conversations. The story continues — survival, art, and second chances.{CTA}",
            f"Good night. Reflecting on another day of telling the real story. Tomorrow brings more art and more life.{CTA}",
        ]
    elif handle == "@btckillas":
        return [
            f"Good morning Killas. BTCK on XRPL — pure meme with real transparency. Check the wallet tracking page.{CTA}",
            f"BTCK is built for fun and transparency. Token + NFT staking is live. 589M tokens set to burn. BTCK NFTs are stakeable and add to liquidity and value.{CTA}",
            f"Quick update: The BTCK community is growing. Full transparency on the wallet — no games. Affiliated with Spray The Chain.{CTA}",
            f"Love the energy in the BTCK replies. Meme culture with real utility on XRPL.{CTA}",
            f"Good night Killas. Another fun day in the BTCK ecosystem. Transparency and burns continue.{CTA}",
        ]
    elif handle == "@getoffmylawn70":
        return [
            f"Good morning. Get Off My Lawn with Grammy Tammy is back soon. Non-scripted, real conversations.{CTA}",
            f"Upcoming space alert: Get Off My Lawn is all about real talk — no script, just good conversation.{CTA}",
            f"Quick note: Our spaces are growing. Come hang with us and Grammy Tammy.{CTA}",
            f"Love the energy from the last space. Get Off My Lawn is where real conversations happen.{CTA}",
            f"Good night. Another great week of spaces with Grammy Tammy. Real talk, real people.{CTA}",
        ]
    else:  # @Mmozley70
        return [
            f"Hey all, can I get a GM? Working across all projects and building new community partnerships.{CTA}",
            f"Good morning. Focused on growing the ecosystem and supporting the communities I've built.{CTA}",
            f"Quick update: New partnerships and conversations happening across the projects.{CTA}",
            f"Love the support and energy from everyone. Building in public and connecting with great people.{CTA}",
            f"Good night. Another productive day building and connecting. Rest up — more coming tomorrow.{CTA}",
        ]


def generate_static_schedule() -> Dict[str, List[str]]:
    accounts = ["@Mmozley70", "@bwtzbearwitness", "@btckillas", "@getoffmylawn70", "@textrpsms"]
    schedule = {}
    for a in accounts:
        posts = _base_posts_for_account(a)
        schedule[a] = [p + f" #XRP #XRPL #MEMES #NFTs #ART #UTILITY" for p in posts]
    return schedule


# ----------------------------- API Endpoints -----------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    """Beautiful dark-mode dashboard — the main daily tool for the team."""
    html = """
    <html>
    <head>
        <title>TextRp Daily Posts • X Growth Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Space+Grotesk:wght@500;600&amp;display=swap');
            
            :root {
                --bg: #0a0a0a;
                --card: #111111;
                --accent: #00ff9d;
            }
            
            body { 
                font-family: 'Inter', system_ui, sans-serif; 
                margin: 0; 
                background: var(--bg); 
                color: #ddd; 
                line-height: 1.5;
            }
            .container { max-width: 1100px; margin: 40px auto; padding: 0 20px; }
            h1 { 
                font-family: 'Space Grotesk', sans-serif; 
                color: #fff; 
                font-size: 2.4rem; 
                margin: 0 0 8px;
                letter-spacing: -1px;
            }
            .subtitle { color: #666; margin-bottom: 32px; font-size: 1.05rem; }
            
            .account { 
                margin: 24px 0; 
                padding: 22px 26px; 
                background: var(--card); 
                border-radius: 16px; 
                border: 1px solid #222;
            }
            .account-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 14px;
            }
            .handle { 
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.35rem; 
                color: #fff; 
                font-weight: 600;
            }
            .post-count { 
                font-size: 0.8rem; 
                background: #1f1f1f; 
                padding: 2px 10px; 
                border-radius: 999px; 
                color: #888;
            }
            
            .post {
                background: #1a1a1a;
                padding: 14px 18px;
                border-radius: 10px;
                margin: 10px 0;
                font-size: 0.95rem;
                position: relative;
                transition: all 0.1s ease;
            }
            .post:hover {
                background: #222;
                transform: translateY(-1px);
            }
            .post button {
                background: var(--accent);
                color: #000;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                font-size: 0.85rem;
                margin-top: 8px;
            }
            .post button:hover { background: #00cc7a; }
            
            .status {
                font-size: 0.7rem;
                padding: 1px 7px;
                border-radius: 4px;
                margin-left: 8px;
            }
            .status.pending { background: #3a2f00; color: #ffcc00; }
            .status.posted { background: #003322; color: #00ff9d; }
            
            .tip {
                background: #111;
                border: 1px solid #222;
                padding: 14px 20px;
                border-radius: 12px;
                font-size: 0.9rem;
                color: #888;
            }
            
            .header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 8px;
            }
            .logo {
                width: 42px;
                height: 42px;
                background: linear-gradient(135deg, #00ff9d, #00cc7a);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #000;
                font-weight: 800;
                font-size: 1.4rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">T</div>
                <div>
                    <h1>TextRp Daily Posts</h1>
                    <div class="subtitle">X Growth Bot • Phase 1 — Human in the loop</div>
                </div>
            </div>

            <div id="posts"></div>

            <div class="tip" style="margin-top: 40px;">
                <strong>Tip:</strong> Posts are generated daily by the worker. 
                Click any post to copy it to your clipboard. 
                After you post manually on X, the status will be trackable in future updates.
                <br><br>
                <strong>Accounts:</strong> @Mmozley70 • @bwtzbearwitness • @btckillas • @getoffmylawn70 • @textrpsms
            </div>
        </div>

        <script>
            async function loadPosts() {
                const res = await fetch('/daily');
                const data = await res.json();
                const container = document.getElementById('posts');
                let html = '';

                for (const acc in data.daily_schedule) {
                    const posts = data.daily_schedule[acc];
                    html += `
                        <div class="account">
                            <div class="account-header">
                                <div class="handle">${acc}</div>
                                <div class="post-count">${posts.length} posts</div>
                            </div>
                    `;
                    
                    posts.forEach((post, idx) => {
                        const safePost = post.replace(/'/g, "\\'").replace(/"/g, '\\"');
                        const statusHtml = post.status 
                            ? `<span class="status ${post.status}">${post.status}</span>` 
                            : '';
                        
                        html += `
                            <div class="post">
                                <div>${post.replace(/\\n/g, '<br>')}</div>
                                <button onclick="copyPost('${safePost}', this)">Copy to clipboard</button>
                                ${statusHtml}
                            </div>
                        `;
                    });
                    
                    html += `</div>`;
                }
                
                container.innerHTML = html || '<p style="color:#666">No posts for today yet. The worker will generate them shortly.</p>';
            }

            function copyPost(text, btn) {
                navigator.clipboard.writeText(text).then(() => {
                    const original = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.style.background = '#00cc7a';
                    setTimeout(() => {
                        btn.textContent = original;
                        btn.style.background = '';
                    }, 1400);
                });
            }

            loadPosts();
            // Refresh every 60s in case worker just wrote new posts
            setInterval(loadPosts, 60000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/daily")
def daily_schedule():
    """
    JSON endpoint used by the gateway, the worker scheduler, and external tools.
    In Phase 1: prefers persisted DB posts when they exist for today.
    Falls back to the original high-quality static templates.
    """
    db_posts = get_todays_posts_from_db()
    
    if db_posts:
        # Return DB-backed posts (with status metadata)
        schedule = {}
        for handle, items in db_posts.items():
            schedule[handle] = [item["content"] for item in items]
        return {
            "status": "success",
            "source": "database",
            "date": str(date.today()),
            "daily_schedule": schedule,
            "tip": "Posts loaded from database (generated by worker). Human review recommended before posting.",
            "powered_by": "XtremeRippleProtocol LLC"
        }
    
    # Fallback to static (original behavior)
    static = generate_static_schedule()
    return {
        "status": "success",
        "source": "template",
        "date": str(date.today()),
        "daily_schedule": static,
        "tip": "Static templates (worker has not persisted today's batch yet or DB is unavailable).",
        "powered_by": "XtremeRippleProtocol LLC"
    }


@app.get("/healthz")
def health():
    return {"ok": True, "service": "agent-orchestrator", "phase": "1"}


# ----------------------------- Future Phase 1 endpoints (stubs for now) -----------------------------

class MarkPostedRequest(BaseModel):
    account: str
    content: str


@app.post("/mark-posted")
def mark_posted(req: MarkPostedRequest):
    """Phase 1 placeholder — will update status in DB."""
    return {"status": "accepted", "message": "Marking as posted will be wired in the next iteration"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)