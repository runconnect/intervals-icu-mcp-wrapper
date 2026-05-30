from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.client import intervals_get, INTERVALS_ATHLETE_ID

router = APIRouter()


def _round_if_number(value: Any, digits: int = 1) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else value


def normalize_activity_summary(activity: Dict[str, Any]) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "id": activity.get("id"),
        "name": activity.get("name") or "Untitled",
        "start_date": (
            activity.get("start_date_local")
            or activity.get("start_date")
            or activity.get("date")
        ),
        "type": activity.get("type") or activity.get("sport") or activity.get("activity_type"),
    }

    if activity.get("description"):
        item["description"] = activity.get("description")

    if activity.get("distance") is not None:
        item["distance_meters"] = activity.get("distance")
    elif activity.get("distance_meters") is not None:
        item["distance_meters"] = activity.get("distance_meters")

    if activity.get("moving_time") is not None:
        item["moving_time_seconds"] = activity.get("moving_time")
    if activity.get("elapsed_time") is not None:
        item["elapsed_time_seconds"] = activity.get("elapsed_time")
    if activity.get("total_elevation_gain") is not None:
        item["elevation_gain_meters"] = activity.get("total_elevation_gain")

    performance: Dict[str, Any] = {}
    for src, dst in [
        ("average_watts", "average_watts"),
        ("normalized_power", "normalized_power"),
        ("average_heartrate", "average_heartrate"),
        ("average_cadence", "average_cadence"),
        ("average_speed", "average_speed_meters_per_sec"),
    ]:
        if activity.get(src) is not None:
            performance[dst] = activity.get(src)
    if performance:
        item["performance"] = performance

    training: Dict[str, Any] = {}
    for src, dst in [
        ("icu_training_load", "training_load"),
        ("icu_intensity", "intensity_factor"),
        ("tss", "tss"),
        ("hrss", "hrss"),
        ("trimp", "trimp"),
    ]:
        if activity.get(src) is not None:
            training[dst] = _round_if_number(activity.get(src), 0 if src in {"tss", "hrss", "trimp"} else 2)
    if training:
        item["training"] = training

    subjective: Dict[str, Any] = {}
    if activity.get("feel") is not None:
        subjective["feel"] = activity.get("feel")
    if activity.get("perceived_exertion") is not None:
        subjective["rpe"] = activity.get("perceived_exertion")
    if subjective:
        item["subjective"] = subjective

    other: Dict[str, Any] = {}
    if activity.get("calories") is not None:
        other["calories"] = activity.get("calories")
    if activity.get("device_name"):
        other["device"] = activity.get("device_name")
    if activity.get("trainer") or activity.get("indoor"):
        other["indoor"] = True
    if activity.get("commute"):
        other["commute"] = True
    if other:
        item["other"] = other

    item["raw_json"] = activity
    return item


def normalize_activity_details(activity: Dict[str, Any]) -> Dict[str, Any]:
    item = normalize_activity_summary(activity)

    power: Dict[str, Any] = {}
    for src, dst in [
        ("average_watts", "average"),
        ("normalized_power", "normalized"),
        ("weighted_average_watts", "weighted_average"),
        ("max_watts", "max"),
        ("variability_index", "variability_index"),
        ("efficiency_factor", "efficiency_factor"),
    ]:
        if activity.get(src) is not None:
            power[dst] = _round_if_number(activity.get(src), 2 if src in {"variability_index", "efficiency_factor"} else 1)
    if power:
        item["power"] = power

    heart_rate: Dict[str, Any] = {}
    if activity.get("average_heartrate") is not None:
        heart_rate["average"] = activity.get("average_heartrate")
    if activity.get("max_heartrate") is not None:
        heart_rate["max"] = activity.get("max_heartrate")
    if heart_rate:
        item["heart_rate"] = heart_rate

    cadence: Dict[str, Any] = {}
    if activity.get("average_cadence") is not None:
        cadence["average"] = activity.get("average_cadence")
    if activity.get("max_cadence") is not None:
        cadence["max"] = activity.get("max_cadence")
    if cadence:
        item["cadence"] = cadence

    speed: Dict[str, Any] = {}
    if activity.get("average_speed") is not None:
        speed["average_meters_per_sec"] = activity.get("average_speed")
    if activity.get("max_speed") is not None:
        speed["max_meters_per_sec"] = activity.get("max_speed")
    if speed:
        item["speed"] = speed

    return item


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
async def get_activities(
    oldest: Optional[str] = None,
    newest: Optional[str] = None,
    structured: bool = Query(
        True,
        description="Si true, renvoie une structure normalisée plus exploitable",
    ),
    limit: Optional[int] = Query(
        None,
        description="Nombre maximum d'activités à retourner après tri décroissant par date",
    ),
):
    activities = await fetch_activities_range(oldest, newest)
    activities.sort(
        key=lambda x: str(
            x.get("start_date_local") or x.get("start_date") or x.get("date") or ""
        ),
        reverse=True,
    )

    if limit is not None and limit >= 0:
        activities = activities[:limit]

    if not structured:
        return JSONResponse(content={"count": len(activities), "activities": activities})

    normalized = [normalize_activity_summary(activity) for activity in activities]
    return JSONResponse(content={"count": len(normalized), "activities": normalized})


@router.get(
    "/activities/details",
    operation_id="get_activity_details",
    tags=["intervals"],
    summary="Get activity details",
    description="Retourne une vue détaillée et normalisée d'une activité.",
)
async def get_activity_details(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    activity = await intervals_get(f"/activity/{activity_id}")
    if not isinstance(activity, dict):
        raise HTTPException(status_code=404, detail=f"Activité introuvable: {activity_id}")

    return JSONResponse(content=normalize_activity_details(activity))


@router.get(
    "/activities/search",
    operation_id="search_activities_local",
    tags=["intervals"],
    summary="Search activities locally",
    description="Recherche locale simple dans une plage d'activités par nom ou description.",
)
async def search_activities_local(
    query: str = Query(..., description="Texte recherché dans name ou description"),
    oldest: Optional[str] = Query(None, description="Date ISO de début incluse"),
    newest: Optional[str] = Query(None, description="Date ISO de fin incluse"),
    limit: int = Query(20, description="Nombre maximum de résultats"),
):
    query_norm = query.strip().lower()
    if not query_norm:
        raise HTTPException(status_code=400, detail="query ne doit pas être vide")

    activities = await fetch_activities_range(oldest, newest)
    matches: List[Dict[str, Any]] = []

    for activity in activities:
        haystack = " ".join(
            [
                str(activity.get("name") or ""),
                str(activity.get("description") or ""),
                str(activity.get("type") or ""),
            ]
        ).lower()
        if query_norm in haystack:
            matches.append(normalize_activity_summary(activity))

    matches.sort(key=lambda x: str(x.get("start_date") or ""), reverse=True)
    matches = matches[: max(limit, 0)]

    return JSONResponse(
        content={
            "query": query,
            "count": len(matches),
            "activities": matches,
        }
    )

@router.get(
    "/activities/search/full",
    operation_id="search_activities_full",
    tags=["intervals"],
    summary="Search activities with full details",
    description="Recherche des activités par nom ou tag, retourne les détails complets (métriques de performance, charge, intensité).",
)
async def search_activities_full(
    query: str = Query(..., description="Texte recherché dans name, description ou tag"),
    limit: int = Query(30, description="Nombre maximum de résultats (max 100)"),
):
    query_norm = query.strip()
    if not query_norm:
        raise HTTPException(status_code=400, detail="query ne doit pas être vide")

    # Appel à l'API native de recherche Intervals.icu
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/activities",
        params={"search": query_norm, "limit": min(limit, 100)},
    )
    activities = data if isinstance(data, list) else []

    # Normalisation enrichie (détails complets)
    normalized = [normalize_activity_details(a) for a in activities]
    normalized.sort(key=lambda x: str(x.get("start_date") or ""), reverse=True)

    return JSONResponse(content={
        "query": query,
        "count": len(normalized),
        "activities": normalized,
    })

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