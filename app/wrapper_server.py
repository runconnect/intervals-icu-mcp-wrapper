import os
import json
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

INTERVALS_API_KEY = os.getenv("INTERVALS_API_KEY")
INTERVALS_ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")
INTERVALS_BASE_URL = "https://intervals.icu/api/v1"

if not INTERVALS_API_KEY or not INTERVALS_ATHLETE_ID:
    raise RuntimeError("INTERVALS_API_KEY et INTERVALS_ATHLETE_ID sont requis")

app = FastAPI(title="Intervals.icu MCP SSE Wrapper")

async def intervals_get(path: str, params: dict | None = None):
    url = f"{INTERVALS_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            params=params,
            auth=(INTERVALS_API_KEY, "api_key"),
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tools")
async def tools():
    return {
        "tools": [
            {"name": "get_activities", "description": "Retourne les activités Intervals.icu"},
            {"name": "get_wellness", "description": "Retourne les métriques wellness"},
            {"name": "get_events", "description": "Retourne les événements"}
        ]
    }

@app.get("/sse")
async def sse_endpoint(request: Request):
    async def event_generator():
        intro = {
            "type": "server.info",
            "server": "intervals-icu-mcp-sse-wrapper",
            "message": "SSE endpoint actif"
        }
        yield {
            "event": "message",
            "data": json.dumps(intro)
        }

        while True:
            if await request.is_disconnected():
                break
            yield {
                "event": "ping",
                "data": json.dumps({"ok": True})
            }
            import asyncio
            await asyncio.sleep(15)

    return EventSourceResponse(event_generator())

@app.get("/activities")
async def get_activities(oldest: str | None = None, newest: str | None = None):
    try:
        data = await intervals_get(
            f"/athlete/{INTERVALS_ATHLETE_ID}/activities",
            params={"oldest": oldest, "newest": newest},
        )
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wellness")
async def get_wellness(oldest: str | None = None, newest: str | None = None):
    try:
        data = await intervals_get(
            f"/athlete/{INTERVALS_ATHLETE_ID}/wellness",
            params={"oldest": oldest, "newest": newest},
        )
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events")
async def get_events(oldest: str | None = None, newest: str | None = None):
    try:
        data = await intervals_get(
            f"/athlete/{INTERVALS_ATHLETE_ID}/events",
            params={"oldest": oldest, "newest": newest},
        )
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
