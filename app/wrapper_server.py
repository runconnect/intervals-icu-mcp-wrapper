import os
from typing import Optional, Dict, Any

import httpx
from fastapi import Request
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP

INTERVALS_API_KEY = os.getenv("INTERVALS_API_KEY")
INTERVALS_ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")
INTERVALS_BASE_URL = "https://intervals.icu/api/v1"

if not INTERVALS_API_KEY or not INTERVALS_ATHLETE_ID:
    raise RuntimeError("INTERVALS_API_KEY et INTERVALS_ATHLETE_ID sont requis")

app = FastAPI(
    title="Intervals.icu MCP HTTP Wrapper",
    version="1.0.0",
    description="Wrapper FastAPI + MCP Streamable HTTP pour Intervals.icu",
)


async def intervals_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{INTERVALS_BASE_URL}{path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params=params,
                auth=("API_KEY", INTERVALS_API_KEY),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise HTTPException(
            status_code=e.response.status_code if e.response is not None else 502,
            detail=f"Erreur Intervals.icu: {detail}",
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur réseau Intervals.icu: {str(e)}",
        )


@app.get("/health", operation_id="health_check", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": "intervals-icu-mcp-http-wrapper",
        "mcp_endpoint": "/mcp",
        "athlete_id": INTERVALS_ATHLETE_ID,
    }


@app.get("/", operation_id="root_info", tags=["system"])
async def root():
    return {
        "name": "Intervals.icu MCP HTTP Wrapper",
        "status": "running",
        "health": "/health",
        "mcp": "/mcp",
        "debug_endpoints": [
            "/activities",
            "/wellness",
            "/events",
        ],
    }


@app.get("/activities", operation_id="get_activities", tags=["intervals"])
async def get_activities(
    oldest: Optional[str] = None,
    newest: Optional[str] = None,
):
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/activities",
        params={"oldest": oldest, "newest": newest},
    )
    return JSONResponse(content=data)


@app.get("/wellness", operation_id="get_wellness", tags=["intervals"])
async def get_wellness(
    oldest: Optional[str] = None,
    newest: Optional[str] = None,
):
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/wellness",
        params={"oldest": oldest, "newest": newest},
    )
    return JSONResponse(content=data)


@app.get("/events", operation_id="get_events", tags=["intervals"])
async def get_events(
    oldest: Optional[str] = None,
    newest: Optional[str] = None,
):
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/events",
        params={"oldest": oldest, "newest": newest},
    )
    return JSONResponse(content=data)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"REQ {request.method} {request.url} headers={dict(request.headers)}")
    response = await call_next(request)
    print(f"RES {request.method} {request.url} -> {response.status_code}")
    return response

mcp = FastApiMCP(
    app,
    name="Intervals.icu Tools",
    description="Expose les endpoints Intervals.icu comme outils MCP via HTTP transport",
    include_operations=[
        "get_activities",
        "get_wellness",
        "get_events",
    ],
)

mcp.mount_http(mount_path="/mcp")