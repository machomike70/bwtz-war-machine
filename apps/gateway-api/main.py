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
            "x_post_preview": "POST /x/post/preview (dry-run to x-twitter-bot)",
            "x_post_queue": "GET/POST /x/post/queue (safe queue for human review)",
            "x_post_confirm": "POST /x/post/confirm (REAL post after confirmation - human-in-loop only)",
            "orchestrator_direct": ORCHESTRATOR_URL,
            "x_twitter_bot_direct": X_TWITTER_BOT_URL,
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


@app.api_route("/mark-posted", methods=["POST"])
async def proxy_mark_posted(request: Request):
    """Proxy mark-posted (status update) to orchestrator for the daily ops dashboard."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{ORCHESTRATOR_URL}/mark-posted", json=body)
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {exc}")


@app.api_route("/trigger-daily", methods=["POST"])
async def proxy_trigger_daily(request: Request):
    """Proxy trigger for manual daily regeneration from the dashboard."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{ORCHESTRATOR_URL}/trigger-daily", json={})
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
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

# X-Twitter-Bot posting engine proxies (Phase 1-2: safe dry-run + human confirmation flow)
# All posting goes through gateway for single entrypoint; dashboard calls these via /x/post/*


@app.api_route("/x/post/preview", methods=["POST"])
async def proxy_x_preview(request: Request):
    """Proxy dry-run preview to x-twitter-bot (shows what would be posted, no real action)."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{X_TWITTER_BOT_URL}/post/preview", json=body)
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"X-Twitter-Bot unavailable: {exc}")


@app.api_route("/x/post/queue", methods=["GET", "POST"])
async def proxy_x_queue(request: Request):
    """Proxy queue operations: GET lists pending, POST adds a post to the safe queue."""
    try:
        body = None
        if request.method == "POST":
            body = await request.json()
        async with httpx.AsyncClient(timeout=15.0) as client:
            if request.method == "POST":
                r = await client.post(f"{X_TWITTER_BOT_URL}/post/queue", json=body)
            else:
                r = await client.get(f"{X_TWITTER_BOT_URL}/post/queue")
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"X-Twitter-Bot unavailable: {exc}")


@app.api_route("/x/post/confirm", methods=["POST"])
async def proxy_x_confirm(request: Request):
    """Proxy the critical confirm step that performs the real X post (after human review)."""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{X_TWITTER_BOT_URL}/post/confirm", json=body)
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"X-Twitter-Bot unavailable: {exc}")


# Update root to document new endpoints
# (the dict in root() is static; in real would be dynamic but sufficient for now)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)