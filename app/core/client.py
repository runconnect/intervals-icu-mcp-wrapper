import os
from typing import Any, Dict, List, Optional, Union

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

async def intervals_post(
    path: str,
    json: Optional[Union[Dict[str, Any], List[Any]]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    url = f"{INTERVALS_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json=json,
                params=_clean(params),
                auth=_auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        _raise(e)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erreur réseau Intervals.icu: {str(e)}")

async def intervals_put(
    path: str,
    json: Optional[Union[Dict[str, Any], List[Any]]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    url = f"{INTERVALS_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                url,
                json=json,
                params=_clean(params),
                auth=_auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        _raise(e)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erreur réseau Intervals.icu: {str(e)}")


async def intervals_delete(
    path: str,
    json: Optional[Union[Dict[str, Any], List[Any]]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    url = f"{INTERVALS_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(
                url,
                json=json,
                params=_clean(params),
                auth=_auth(),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            # DELETE peut retourner 204 No Content (corps vide)
            if response.status_code == 204 or not response.content:
                return {"deleted": True}
            return response.json()
    except httpx.HTTPStatusError as e:
        _raise(e)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erreur réseau Intervals.icu: {str(e)}")