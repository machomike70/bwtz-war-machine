from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="TextRp AI Stack Gateway", version="0.1.0")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://agent-orchestrator:8001")
X_TWITTER_BOT_URL = os.getenv("X_TWITTER_BOT_URL", "http://x-twitter-bot:8008")  # placeholder for future

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "gateway",
        "version": "0.1.0",
        "description": "TextRp X Growth Bot API Gateway - AI STACK",
        "endpoints": {
            "health": "/healthz",
            "daily_posts": "GET /daily (proxied to orchestrator)",
            "orchestrator_direct": ORCHESTRATOR_URL,
        },
    }

@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "gateway", "status": "healthy"}

@app.get("/health")
async def health():
    """Aggregate health of downstream services"""
    results = {"gateway": "healthy"}
    
    # Check orchestrator
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/")
            results["agent-orchestrator"] = "healthy" if r.status_code == 200 else f"error:{r.status_code}"
    except Exception as e:
        results["agent-orchestrator"] = f"down: {str(e)[:80]}"
    
    return results

@app.api_route("/daily", methods=["GET"])
async def proxy_daily(request: Request):
    """Proxy daily schedule requests to the agent-orchestrator"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/daily")
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {exc}")

@app.get("/orchestrate")
async def proxy_orchestrate():
    """Proxy orchestrate endpoint (for future growth bot flows)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/orchestrate")
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

# Future: Add more proxy routes for x-twitter-bot, retrieval, etc. as they come online

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)