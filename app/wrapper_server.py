import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

# S'assurer que le répertoire contenant ce fichier (/app dans le conteneur)
# est dans le PYTHONPATH, pour que `core` soit importable.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP

from core.client import intervals_get, INTERVALS_ATHLETE_ID
from core.utils import (
    parse_date_value,
    get_activity_date,
    is_run_activity,
    get_distance_meters,
)

# import tools in wrapper_server.py
from routes.plans import router as plans_router
from routes.wellness import router as wellness_router
from routes.activities import router as activities_router

app = FastAPI(
    title="Intervals.icu MCP HTTP Wrapper",
    version="1.2.1",
    description="Wrapper FastAPI + MCP Streamable HTTP pour Intervals.icu avec outils analytiques",
)

app.include_router(plans_router)
app.include_router(wellness_router)
app.include_router(activities_router)

"""
"""
async def fetch_activities_range(oldest: Optional[str], newest: Optional[str]) -> List[Dict[str, Any]]:
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/activities",
        params={"oldest": oldest, "newest": newest},
    )
    return data if isinstance(data, list) else []

def build_histogram_response(activity_id: str, raw_data: Any, metric: str) -> Dict[str, Any]:
    bins = raw_data.get("bins", []) if isinstance(raw_data, dict) else []
    result_bins: List[Dict[str, Any]] = []

    for bin_item in bins:
        item: Dict[str, Any] = {
            "count": bin_item.get("count"),
        }

        if bin_item.get("secs") is not None:
            item["time_seconds"] = bin_item.get("secs")

        if metric == "power":
            item["power_range"] = {
                "min_watts": int(bin_item.get("min", 0)),
                "max_watts": int(bin_item.get("max", 0)),
            }
        elif metric == "hr":
            item["hr_range"] = {
                "min_bpm": int(bin_item.get("min", 0)),
                "max_bpm": int(bin_item.get("max", 0)),
            }
        elif metric == "pace":
            min_val = float(bin_item.get("min", 0))
            max_val = float(bin_item.get("max", 0))
            min_minutes = int(min_val)
            min_seconds = int(round((min_val - min_minutes) * 60))
            max_minutes = int(max_val)
            max_seconds = int(round((max_val - max_minutes) * 60))
            item["pace_range"] = {
                "min_pace_min_per_km": min_val,
                "max_pace_min_per_km": max_val,
                "min_pace_formatted": f"{min_minutes}:{min_seconds:02d} /km",
                "max_pace_formatted": f"{max_minutes}:{max_seconds:02d} /km",
            }

        result_bins.append(item)

    result: Dict[str, Any] = {
        "activity_id": activity_id,
        "bins": result_bins,
        "bin_count": len(result_bins),
    }

    if isinstance(raw_data, dict):
        if raw_data.get("total_count") is not None:
            result["total_samples"] = raw_data.get("total_count")
        if raw_data.get("total_secs") is not None:
            result["total_time_seconds"] = raw_data.get("total_secs")

    return result


def is_effort_usable(effort: Dict[str, Any]) -> bool:
    keys_to_check = [
        "name",
        "elapsed_time",
        "moving_time",
        "distance",
        "average_watts",
        "normalized_power",
        "average_heartrate",
        "average_cadence",
        "average_speed",
        "start_index",
        "end_index",
    ]
    return any(effort.get(k) is not None for k in keys_to_check)


def normalize_best_efforts_payload(activity_id: str, data: Any) -> Dict[str, Any]:
    efforts = data if isinstance(data, list) else []
    normalized: List[Dict[str, Any]] = []

    for effort in efforts:
        item: Dict[str, Any] = {
            "name": effort.get("name"),
            "elapsed_time_seconds": effort.get("elapsed_time"),
            "moving_time_seconds": effort.get("moving_time"),
            "distance_meters": effort.get("distance"),
        }

        performance: Dict[str, Any] = {}
        for src, dst in [
            ("average_watts", "average_watts"),
            ("normalized_power", "normalized_power"),
            ("average_heartrate", "average_heartrate"),
            ("average_cadence", "average_cadence"),
            ("average_speed", "average_speed_meters_per_sec"),
        ]:
            if effort.get(src) is not None:
                performance[dst] = effort.get(src)

        if performance:
            item["performance"] = performance

        if effort.get("start_index") is not None:
            item["start_index"] = effort.get("start_index")
        if effort.get("end_index") is not None:
            item["end_index"] = effort.get("end_index")

        normalized.append(item)

    return {
        "activity_id": activity_id,
        "count": len(normalized),
        "best_efforts": normalized,
    }


@app.get("/health", operation_id="health_check", tags=["system"], summary="Health check")
async def health():
    return {
        "status": "ok",
        "service": "intervals-icu-mcp-http-wrapper",
        "mcp_endpoint": "/mcp",
        "athlete_id": INTERVALS_ATHLETE_ID,
        "version": "1.2.1",
    }


@app.get("/", operation_id="root_info", tags=["system"], summary="Root information")
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
            "/plan-workouts/filtered",
            "/activity-streams",
            "/activity-intervals",
            "/best-efforts",
            "/best-efforts-debug",
            "/power-histogram",
            "/hr-histogram",
            "/pace-histogram",
            "/running-volume-by-week",
        ],
    }

"""
@app.get(
    "/activities",
    operation_id="get_activities",
    tags=["intervals"],
    summary="Get activities",
    description="Retourne les activités Intervals.icu sur une plage de dates ISO optional oldest/newest.",
)
async def get_activities(oldest: Optional[str] = None, newest: Optional[str] = None):
    data = await fetch_activities_range(oldest, newest)
    return JSONResponse(content=data)

@app.get(
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
"""

@app.get(
    "/activity-streams",
    operation_id="get_activity_streams",
    tags=["analysis"],
    summary="Get activity streams",
    description="Retourne les streams d'une activité en utilisant la signature réelle Intervals.icu types + streams.json.",
)
async def get_activity_streams(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
    types: Optional[str] = Query(None, description="Liste de streams séparés par des virgules, ex: watts,heartrate,cadence"),
):
    params: Dict[str, Any] = {}
    if types:
        params["types"] = types
    data = await intervals_get(f"/activity/{activity_id}/streams.json", params=params)
    available_streams = [k for k, v in data.items() if isinstance(v, list)] if isinstance(data, dict) else []
    stream_lengths = {k: len(v) for k, v in data.items() if isinstance(v, list)} if isinstance(data, dict) else {}
    result = {
        "activity_id": activity_id,
        "available_streams": available_streams,
        "stream_lengths": stream_lengths,
        "streams": data,
    }
    return JSONResponse(content=result)


@app.get(
    "/activity-intervals",
    operation_id="get_activity_intervals",
    tags=["analysis"],
    summary="Get activity intervals",
    description="Retourne les intervalles/segments structurés d'une activité avec performances et résumé.",
)
async def get_activity_intervals(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    data = await intervals_get(f"/activity/{activity_id}/intervals")
    intervals = data if isinstance(data, list) else []
    intervals_data: List[Dict[str, Any]] = []

    work_intervals = 0
    rest_intervals = 0
    total_work_time = 0

    for interval in intervals:
        interval_type = interval.get("type")
        interval_item: Dict[str, Any] = {
            "id": interval.get("id"),
            "type": interval_type,
        }

        if interval.get("start") is not None:
            interval_item["start_seconds"] = interval.get("start")
        if interval.get("end") is not None:
            interval_item["end_seconds"] = interval.get("end")
        if interval.get("duration") is not None:
            interval_item["duration_seconds"] = interval.get("duration")

        performance: Dict[str, Any] = {}
        for src, dst in [
            ("average_watts", "average_watts"),
            ("normalized_power", "normalized_power"),
            ("average_heartrate", "average_heartrate"),
            ("max_heartrate", "max_heartrate"),
            ("average_cadence", "average_cadence"),
            ("average_speed", "average_speed_meters_per_sec"),
            ("distance", "distance_meters"),
        ]:
            if interval.get(src) is not None:
                performance[dst] = interval.get(src)

        if performance:
            interval_item["performance"] = performance

        if interval.get("target"):
            interval_item["target_description"] = interval.get("target")
        if interval.get("target_min") is not None or interval.get("target_max") is not None:
            interval_item["target_range"] = {
                "min": interval.get("target_min"),
                "max": interval.get("target_max"),
            }

        if isinstance(interval_type, str) and "WORK" in interval_type.upper():
            work_intervals += 1
            if isinstance(interval.get("duration"), (int, float)):
                total_work_time += int(interval.get("duration"))

        if isinstance(interval_type, str) and "REST" in interval_type.upper():
            rest_intervals += 1

        intervals_data.append(interval_item)

    return JSONResponse(
        content={
            "activity_id": activity_id,
            "count": len(intervals_data),
            "intervals": intervals_data,
            "summary": {
                "total_intervals": len(intervals_data),
                "work_intervals": work_intervals,
                "rest_intervals": rest_intervals,
                "total_work_time_seconds": total_work_time,
            },
        }
    )


@app.get(
    "/best-efforts",
    operation_id="get_best_efforts",
    tags=["analysis"],
    summary="Get best efforts",
    description="Retourne les meilleures performances d'une activité avec une interface alignée sur activity_analysis.py.",
)
async def get_best_efforts(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    data = await intervals_get(f"/activity/{activity_id}/best-efforts")
    return JSONResponse(content=normalize_best_efforts_payload(activity_id, data))

@app.get(
    "/best-efforts-debug",
    operation_id="get_best_efforts_debug",
    tags=["analysis"],
    summary="Debug best efforts",
    description="Endpoint de diagnostic pour l'API Intervals.icu avec paramètres stream, duration et distance, et indicateurs de qualité de réponse.",
)
async def get_best_efforts_debug(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
    stream: str = Query(..., description="Stream requis par l'API Intervals.icu, ex: power, pace, hr"),
    duration: Optional[int] = Query(None, description="Durée cible en secondes pour rechercher la meilleure performance, ex: 300 pour 5 minutes"),
    distance: Optional[int] = Query(None, description="Distance cible en mètres pour rechercher la meilleure performance, ex: 5000 pour 5 km"),
):
    if duration is None and distance is None:
        raise HTTPException(
            status_code=400,
            detail="Au moins un paramètre duration ou distance doit être fourni",
        )

    params: Dict[str, Any] = {"stream": stream}
    if duration is not None:
        params["duration"] = duration
    if distance is not None:
        params["distance"] = distance

    data = await intervals_get(f"/activity/{activity_id}/best-efforts", params=params)

    efforts = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    normalized: List[Dict[str, Any]] = []
    usable_count = 0

    for effort in efforts:
        usable = is_effort_usable(effort)
        if usable:
            usable_count += 1

        item: Dict[str, Any] = {
            "usable": usable,
            "name": effort.get("name"),
            "elapsed_time_seconds": effort.get("elapsed_time"),
            "moving_time_seconds": effort.get("moving_time"),
            "distance_meters": effort.get("distance"),
        }

        performance: Dict[str, Any] = {}
        for src, dst in [
            ("average_watts", "average_watts"),
            ("normalized_power", "normalized_power"),
            ("average_heartrate", "average_heartrate"),
            ("average_cadence", "average_cadence"),
            ("average_speed", "average_speed_meters_per_sec"),
        ]:
            if effort.get(src) is not None:
                performance[dst] = effort.get(src)

        if performance:
            item["performance"] = performance

        if effort.get("start_index") is not None:
            item["start_index"] = effort.get("start_index")
        if effort.get("end_index") is not None:
            item["end_index"] = effort.get("end_index")

        normalized.append(item)

    all_null = len(normalized) > 0 and usable_count == 0

    return JSONResponse(
        content={
            "activity_id": activity_id,
            "stream": stream,
            "duration": duration,
            "distance": distance,
            "count": len(normalized),
            "usable_count": usable_count,
            "all_null": all_null,
            "message": (
                "Aucune donnée exploitable renvoyée par Intervals.icu pour cette combinaison de paramètres"
                if all_null
                else None
            ),
            "best_efforts": normalized,
        }
    )

@app.get(
    "/power-histogram",
    operation_id="get_power_histogram",
    tags=["analysis"],
    summary="Get power histogram",
    description="Retourne l'histogramme de distribution de puissance d'une activité.",
)
async def get_power_histogram(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    data = await intervals_get(f"/activity/{activity_id}/power-histogram")
    return JSONResponse(content=build_histogram_response(activity_id, data, "power"))


@app.get(
    "/hr-histogram",
    operation_id="get_hr_histogram",
    tags=["analysis"],
    summary="Get heart rate histogram",
    description="Retourne l'histogramme de distribution de fréquence cardiaque d'une activité.",
)
async def get_hr_histogram(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    data = await intervals_get(f"/activity/{activity_id}/hr-histogram")
    return JSONResponse(content=build_histogram_response(activity_id, data, "hr"))

@app.get(
    "/pace-histogram",
    operation_id="get_pace_histogram",
    tags=["analysis"],
    summary="Get pace histogram",
    description="Retourne l'histogramme de distribution d'allure d'une activité, avec plages formatées en min/km.",
)
async def get_pace_histogram(
    activity_id: str = Query(..., description="Identifiant de l'activité Intervals.icu"),
):
    data = await intervals_get(f"/activity/{activity_id}/pace-histogram")
    return JSONResponse(content=build_histogram_response(activity_id, data, "pace"))

@app.get(
    "/running-volume-by-week",
    operation_id="get_running_volume_by_week",
    tags=["analysis"],
    summary="Get weekly running volume",
    description="Retourne le volume hebdomadaire de course sur route ou trail par semaine ISO, en kilomètres.",
)
async def get_running_volume_by_week(
    oldest: str = Query(..., description="Date ISO de début incluse, ex: 2026-01-01"),
    newest: str = Query(..., description="Date ISO de fin incluse, ex: 2026-01-31"),
):
    start = parse_date_value(oldest)
    end = parse_date_value(newest)
    if not start or not end:
        raise HTTPException(status_code=400, detail="oldest et newest doivent être des dates ISO valides YYYY-MM-DD")
    if start > end:
        raise HTTPException(status_code=400, detail="oldest doit être antérieure ou égale à newest")

    activities = await fetch_activities_range(oldest, newest)
    weekly = defaultdict(lambda: {"distance_meters": 0.0, "activity_count": 0, "activities": []})
    total_run_activities = 0

    for activity in activities:
        activity_date = get_activity_date(activity)
        if not activity_date or not (start <= activity_date <= end):
            continue
        if not is_run_activity(activity):
            continue

        total_run_activities += 1
        week_start = activity_date - timedelta(days=activity_date.weekday())
        dist_m = get_distance_meters(activity)

        bucket = weekly[week_start.isoformat()]
        bucket["distance_meters"] += dist_m
        bucket["activity_count"] += 1
        bucket["activities"].append(
            {
                "id": activity.get("id"),
                "date": activity_date.isoformat(),
                "name": activity.get("name"),
                "type": activity.get("type") or activity.get("sport") or activity.get("activity_type"),
                "distance_km": round(dist_m / 1000.0, 2),
            }
        )

    weeks = []
    for week_start in sorted(weekly.keys()):
        week_end = date.fromisoformat(week_start) + timedelta(days=6)
        weeks.append(
            {
                "week_start": week_start,
                "week_end": week_end.isoformat(),
                "activity_count": weekly[week_start]["activity_count"],
                "distance_km": round(weekly[week_start]["distance_meters"] / 1000.0, 2),
                "activities": weekly[week_start]["activities"],
            }
        )

    return JSONResponse(
        content={
            "sport": "Run",
            "oldest": oldest,
            "newest": newest,
            "weeks": weeks,
            "summary": {
                "week_count": len(weeks),
                "run_activity_count": total_run_activities,
                "total_distance_km": round(sum(w["distance_km"] for w in weeks), 2),
            },
        }
    )


mcp = FastApiMCP(
    app,
    name="Intervals.icu Tools",
    description="Expose des outils Intervals.icu bruts et analytiques via MCP HTTP transport.",
    include_operations=[
        "get_activities",
        "get_wellness",
        "get_events",
        "get_plan_workouts_filtered",
        "get_activity_streams",
        "get_activity_intervals",
        "get_best_efforts",
        "get_best_efforts_debug",
        "get_power_histogram",
        "get_hr_histogram",
        "get_pace_histogram",
        "get_running_volume_by_week",
    ],
)

mcp.mount_http(mount_path="/mcp")