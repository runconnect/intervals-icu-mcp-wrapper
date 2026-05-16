from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.client import intervals_get, INTERVALS_ATHLETE_ID

router = APIRouter()


def _round_if_number(value: Any, digits: int = 1) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else value


def normalize_wellness_record(record: Dict[str, Any]) -> Dict[str, Any]:
    day_data: Dict[str, Any] = {
        "date": record.get("id") or record.get("date")
    }

    sleep: Dict[str, Any] = {}
    if record.get("sleepSecs") is not None:
        sleep["duration_seconds"] = record.get("sleepSecs")
    if record.get("sleepQuality") is not None:
        sleep["quality"] = record.get("sleepQuality")
    if record.get("sleepScore") is not None:
        sleep["score"] = _round_if_number(record.get("sleepScore"), 0)
    if record.get("avgSleepingHR") is not None:
        sleep["avg_sleeping_hr"] = _round_if_number(record.get("avgSleepingHR"), 0)
    if sleep:
        day_data["sleep"] = sleep

    heart: Dict[str, Any] = {}
    if record.get("hrv") is not None:
        heart["hrv_rmssd"] = _round_if_number(record.get("hrv"), 1)
    if record.get("hrvSDNN") is not None:
        heart["hrv_sdnn"] = _round_if_number(record.get("hrvSDNN"), 1)
    if record.get("restingHR") is not None:
        heart["resting_hr"] = record.get("restingHR")
    if record.get("baevskySI") is not None:
        heart["baevsky_si"] = _round_if_number(record.get("baevskySI"), 1)
    if heart:
        day_data["heart"] = heart

    subjective: Dict[str, Any] = {}
    for src, dst in [
        ("fatigue", "fatigue"),
        ("soreness", "soreness"),
        ("stress", "stress"),
        ("mood", "mood"),
        ("motivation", "motivation"),
        ("injury", "injury"),
    ]:
        if record.get(src) is not None:
            subjective[dst] = record.get(src)
    if record.get("readiness") is not None:
        subjective["readiness"] = _round_if_number(record.get("readiness"), 0)
    if subjective:
        day_data["subjective"] = subjective

    body: Dict[str, Any] = {}
    if record.get("weight") is not None:
        body["weight_kg"] = record.get("weight")
    if record.get("bodyFat") is not None:
        body["body_fat_percent"] = _round_if_number(record.get("bodyFat"), 1)
    if body:
        day_data["body"] = body

    vitals: Dict[str, Any] = {}
    if record.get("systolic") is not None:
        vitals["systolic_mmhg"] = record.get("systolic")
    if record.get("diastolic") is not None:
        vitals["diastolic_mmhg"] = record.get("diastolic")
    if record.get("spo2") is not None:
        vitals["spo2_percent"] = _round_if_number(record.get("spo2"), 1)
    if record.get("respiration") is not None:
        vitals["respiration_rate"] = _round_if_number(record.get("respiration"), 1)
    if vitals:
        day_data["vitals"] = vitals

    activity_nutrition: Dict[str, Any] = {}
    if record.get("steps") is not None:
        activity_nutrition["steps"] = record.get("steps")
    if record.get("kcalConsumed") is not None:
        activity_nutrition["calories_consumed"] = record.get("kcalConsumed")
    if record.get("hydrationVolume") is not None:
        activity_nutrition["hydration_liters"] = _round_if_number(record.get("hydrationVolume"), 1)
    if activity_nutrition:
        day_data["activity_nutrition"] = activity_nutrition

    training: Dict[str, Any] = {}
    if record.get("ctl") is not None:
        training["ctl"] = _round_if_number(record.get("ctl"), 1)
    if record.get("atl") is not None:
        training["atl"] = _round_if_number(record.get("atl"), 1)
    if record.get("tsb") is not None:
        training["tsb"] = _round_if_number(record.get("tsb"), 1)
    if record.get("rampRate") is not None:
        training["ramp_rate"] = _round_if_number(record.get("rampRate"), 1)
    if training:
        day_data["training"] = training

    other: Dict[str, Any] = {}
    if record.get("bloodGlucose") is not None:
        other["blood_glucose_mmol_per_l"] = _round_if_number(record.get("bloodGlucose"), 1)
    if record.get("lactate") is not None:
        other["lactate_mmol_per_l"] = _round_if_number(record.get("lactate"), 1)
    if record.get("menstrualPhase") is not None:
        other["menstrual_phase"] = record.get("menstrualPhase")
    if other:
        day_data["other"] = other

    if record.get("comments"):
        day_data["comments"] = record.get("comments")

    day_data["raw_json"] = record
    return day_data


def build_wellness_trends(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    trends: Dict[str, Any] = {}
    if len(records) < 2:
        return trends

    def metric_values(key: str) -> List[Any]:
        return [r.get(key) for r in records if r.get(key) is not None]

    hrv_values = metric_values("hrv")
    if len(hrv_values) >= 2:
        trends["hrv"] = {
            "current": _round_if_number(hrv_values[0], 1),
            "change": _round_if_number(hrv_values[0] - hrv_values[-1], 1),
        }

    rhr_values = metric_values("restingHR")
    if len(rhr_values) >= 2:
        trends["resting_hr"] = {
            "current": rhr_values[0],
            "change": rhr_values[0] - rhr_values[-1],
        }

    sleep_quality_values = metric_values("sleepQuality")
    if len(sleep_quality_values) >= 2:
        trends["avg_sleep_quality"] = round(
            sum(sleep_quality_values) / len(sleep_quality_values), 1
        )

    weight_values = metric_values("weight")
    if len(weight_values) >= 2:
        trends["weight"] = {
            "current": weight_values[0],
            "change": _round_if_number(weight_values[0] - weight_values[-1], 1),
        }

    return trends


@router.get(
    "/wellness",
    operation_id="get_wellness",
    tags=["intervals"],
    summary="Get wellness entries",
    description="Retourne les entrées wellness Intervals.icu sur une plage de dates ISO optional oldest/newest.",
)
async def get_wellness(
    oldest: Optional[str] = None,
    newest: Optional[str] = None,
    structured: bool = Query(
        True,
        description="Si true, renvoie une structure normalisée par catégories (sleep, heart, subjective, etc.)",
    ),
    include_trends: bool = Query(
        True,
        description="Si true, calcule des tendances simples sur la plage demandée",
    ),
):
    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/wellness",
        params={"oldest": oldest, "newest": newest},
    )

    records = data if isinstance(data, list) else []
    records.sort(key=lambda x: str(x.get("id", "")), reverse=True)

    if not structured:
        return JSONResponse(
            content={
                "count": len(records),
                "wellness_data": records,
            }
        )

    normalized = [normalize_wellness_record(record) for record in records]

    response: Dict[str, Any] = {
        "count": len(normalized),
        "wellness_data": normalized,
    }

    if include_trends:
        trends = build_wellness_trends(records)
        if trends:
            response["trends"] = trends

    return JSONResponse(content=response)


@router.get(
    "/wellness/date",
    operation_id="get_wellness_for_date",
    tags=["intervals"],
    summary="Get wellness for date",
    description="Retourne les métriques wellness d'une date précise, avec structure normalisée.",
)
async def get_wellness_for_date(
    date: str = Query(..., description="Date ISO YYYY-MM-DD"),
):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date doit être au format YYYY-MM-DD")

    data = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/wellness",
        params={"oldest": date, "newest": date},
    )

    records = data if isinstance(data, list) else []
    if not records:
        raise HTTPException(status_code=404, detail=f"Aucune donnée wellness trouvée pour {date}")

    record = records[0]
    return JSONResponse(content=normalize_wellness_record(record))