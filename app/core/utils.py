from datetime import date
from typing import Any, Dict, Optional


def parse_date_value(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    raw = value[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def get_activity_date(activity: Dict[str, Any]) -> Optional[date]:
    for key in ["start_date_local", "start_date", "date", "activity_date"]:
        parsed = parse_date_value(activity.get(key))
        if parsed:
            return parsed
    return None


def is_run_activity(activity: Dict[str, Any]) -> bool:
    candidates = [
        activity.get("type"),
        activity.get("sport"),
        activity.get("activity_type"),
        activity.get("category"),
    ]
    normalized = {str(v).strip().lower() for v in candidates if v is not None}
    return any(v in {"run", "running", "trail run", "trail_running"} for v in normalized)


def get_distance_meters(activity: Dict[str, Any]) -> float:
    for key in ["distance", "distance_meters"]:
        value = activity.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    if isinstance(activity.get("distanceKm"), (int, float)):
        return float(activity["distanceKm"]) * 1000.0
    return 0.0