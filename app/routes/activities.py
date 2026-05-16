from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.client import intervals_get, INTERVALS_ATHLETE_ID

router = APIRouter()


async def fetch_activities_range(oldest: Optional[str], newest: Optional[str]) -> List[Dict[str, Any]]:
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/activities",
        params={"oldest": oldest, "newest": newest},
    )
    return data if isinstance(data, list) else []


@router.get(
    "/activities",
    operation_id="get_activities",
    tags=["intervals"],
    summary="Get activities",
    description="Retourne les activités Intervals.icu sur une plage de dates ISO optional oldest/newest.",
)
async def get_activities(oldest: Optional[str] = None, newest: Optional[str] = None):
    data = await fetch_activities_range(oldest, newest)
    return JSONResponse(content=data)


@router.get(
    "/events",
    operation_id="get_events",
    tags=["intervals"],
    summary="Get calendar events",
    description="Retourne les événements calendrier Intervals.icu sur une plage de dates ISO optional oldest/newest.",
)
async def get_events(oldest: Optional[str] = None, newest: Optional[str] = None):
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/events",
        params={"oldest": oldest, "newest": newest},
    )
    return JSONResponse(content=data)