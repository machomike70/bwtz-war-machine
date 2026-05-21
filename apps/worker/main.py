"""
TextRp X Growth Bot - Worker Service (Phase 1)

Responsible for:
- Running the daily scheduler (APScheduler)
- Generating / fetching daily posts from orchestrator
- Persisting them to Postgres with status tracking
- Future: triggering X posting jobs (dry-run / queued)

This runs as a long-lived container (like the old stub).
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from psycopg import connect
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] worker: %(message)s")
logger = logging.getLogger("worker")

# Config
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://agent-orchestrator:8001")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_stack:change-me@postgres:5432/ai_stack")
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
DAILY_POST_TIMES = os.getenv("DAILY_POST_TIMES", "08:00,20:00")  # comma separated HH:MM
POST_JITTER_SECONDS = int(os.getenv("POST_JITTER_SECONDS", "300"))

ACCOUNTS = ["@Mmozley70", "@bwtzbearwitness", "@btckillas", "@getoffmylawn70", "@textrpsms"]

# DB connection
def get_db():
    return connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def init_db():
    """Create tables if they don't exist (simple, no migrations yet)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    handle TEXT UNIQUE NOT NULL,
                    brand TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_posts (
                    id SERIAL PRIMARY KEY,
                    account_handle TEXT NOT NULL,
                    content TEXT NOT NULL,
                    scheduled_for DATE NOT NULL,
                    status TEXT DEFAULT 'pending',   -- pending, approved, posted, skipped
                    source TEXT DEFAULT 'template',  -- template, ai_generated, manual
                    posted_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (account_handle, scheduled_for, content)
                );
            """)
            # Seed accounts
            for handle in ACCOUNTS:
                cur.execute(
                    "INSERT INTO accounts (handle) VALUES (%s) ON CONFLICT (handle) DO NOTHING",
                    (handle,)
                )
    logger.info("Database initialized (tables + seed accounts ready)")


def fetch_or_generate_daily() -> Dict[str, List[str]]:
    """
    Call the orchestrator to get today's posts.
    In Phase 1 this is still the static template logic.
    In Phase 2+ this will be enhanced with DB history + AI.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{ORCHESTRATOR_URL}/daily")
            resp.raise_for_status()
            data = resp.json()
            return data.get("daily_schedule", {})
    except Exception as e:
        logger.error(f"Failed to reach orchestrator: {e}")
        # Fallback: empty so we don't crash the job
        return {}


def persist_daily_posts(schedule: Dict[str, List[str]], for_date: date):
    """Insert generated posts for today if they don't already exist."""
    inserted = 0
    with get_db() as conn:
        with conn.cursor() as cur:
            for handle, posts in schedule.items():
                for content in posts:
                    cur.execute(
                        """
                        INSERT INTO daily_posts (account_handle, content, scheduled_for, status, source)
                        VALUES (%s, %s, %s, 'pending', 'template')
                        ON CONFLICT (account_handle, scheduled_for, content) DO NOTHING
                        """,
                        (handle, content, for_date)
                    )
                    if cur.rowcount > 0:
                        inserted += 1
    logger.info(f"Persisted {inserted} new daily posts for {for_date}")


def scheduled_job():
    """The actual daily generation job."""
    today = date.today()
    logger.info(f"Running daily post generation job for {today}")
    schedule = fetch_or_generate_daily()
    if schedule:
        persist_daily_posts(schedule, today)
    else:
        logger.warning("No schedule data returned — skipping persist")


def get_todays_posts() -> List[Dict[str, Any]]:
    """Helper for the orchestrator to read from DB (future integration)."""
    today = date.today()
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
            return cur.fetchall()


def start_scheduler():
    """Configure and start APScheduler with the times from env."""
    scheduler = BackgroundScheduler(timezone="UTC")  # or "America/Los_Angeles" etc.

    times = [t.strip() for t in DAILY_POST_TIMES.split(",") if t.strip()]
    for t in times:
        hour, minute = map(int, t.split(":"))
        trigger = CronTrigger(hour=hour, minute=minute, second=0)
        scheduler.add_job(
            scheduled_job,
            trigger=trigger,
            id=f"daily_posts_{t}",
            name=f"Generate daily posts at {t}",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily job at {t} UTC")

    scheduler.start()
    logger.info("APScheduler started for TextRp X Growth Bot")
    return scheduler


def main():
    logger.info("TextRp Worker starting...")
    init_db()

    if SCHEDULER_ENABLED:
        sched = start_scheduler()
    else:
        logger.info("Scheduler disabled via env (SCHEDULER_ENABLED=false)")

    # Keep the process alive. In production you might also expose a small FastAPI
    # for manual trigger (/trigger-daily, /status, etc.).
    # For now we just sleep forever (or run uvicorn if we add an app).
    logger.info("Worker is running. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")


if __name__ == "__main__":
    main()