from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="XtremeRippleProtocol X Growth Bot")

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