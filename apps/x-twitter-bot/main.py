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