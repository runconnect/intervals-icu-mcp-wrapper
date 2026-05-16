import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

INTERVALS_API_KEY = os.getenv("INTERVALS_API_KEY")
INTERVALS_ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")
INTERVALS_BASE_URL = "https://intervals.icu/api/v1"

if not INTERVALS_API_KEY or not INTERVALS_ATHLETE_ID:
    raise RuntimeError("INTERVALS_API_KEY et INTERVALS_ATHLETE_ID sont requis")


async def intervals_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{INTERVALS_BASE_URL}{path}"
    cleaned_params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                params=cleaned_params,
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
        raise HTTPException(status_code=502, detail=f"Erreur réseau Intervals.icu: {str(e)}")