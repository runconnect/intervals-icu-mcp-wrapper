from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.client import intervals_get, INTERVALS_ATHLETE_ID

router = APIRouter()


def _round_if_number(value: Any, digits: int = 1) -> Any:
    return round(value, digits) if isinstance(value, (int, float)) else value


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def build_form_analysis(tsb: Any) -> Dict[str, Any]:
    if not isinstance(tsb, (int, float)):
        return {}

    if tsb > 20:
        return {
            "form_status": "very_fresh",
            "form_description": "Très frais, profil favorable pour une course ou une séance clé.",
        }
    if tsb > 5:
        return {
            "form_status": "recovered",
            "form_description": "Récupéré et prêt pour un entraînement soutenu.",
        }
    if tsb > -10:
        return {
            "form_status": "optimal",
            "form_description": "Zone généralement productive pour l'entraînement.",
        }
    if tsb > -30:
        return {
            "form_status": "fatigued",
            "form_description": "Fatigue en accumulation, récupération à surveiller.",
        }
    return {
        "form_status": "very_fatigued",
        "form_description": "Fatigue élevée, priorité à la récupération.",
    }


def build_ramp_rate_analysis(ramp_rate: Any) -> Dict[str, Any]:
    if not isinstance(ramp_rate, (int, float)):
        return {}

    if ramp_rate > 8:
        return {
            "ramp_rate_status": "high_risk",
            "ramp_rate_description": "Progression de charge très rapide.",
            "ramp_rate_warning": "Réduire la charge pour limiter le risque de surmenage.",
        }
    if ramp_rate > 5:
        return {
            "ramp_rate_status": "caution",
            "ramp_rate_description": "Progression de charge rapide.",
            "ramp_rate_warning": "Surveiller la fatigue et la récupération de près.",
        }
    if ramp_rate > 0:
        return {
            "ramp_rate_status": "good",
            "ramp_rate_description": "Progression de fitness soutenable.",
        }
    if ramp_rate > -5:
        return {
            "ramp_rate_status": "declining",
            "ramp_rate_description": "Fitness légèrement en baisse, compatible avec une phase d'allègement.",
        }
    return {
        "ramp_rate_status": "declining_significantly",
        "ramp_rate_description": "Fitness en baisse marquée.",
    }


def build_training_recommendations(tsb: Any, ramp_rate: Any) -> List[str]:
    if not isinstance(tsb, (int, float)) or not isinstance(ramp_rate, (int, float)):
        return []

    recommendations: List[str] = []

    if tsb < -30:
        recommendations.append("Prévoir des jours faciles ou du repos.")
        recommendations.append("Favoriser la récupération et les intensités basses.")
    elif tsb < -10 and ramp_rate > 5:
        recommendations.append("Mieux équilibrer charge élevée et récupération.")
        recommendations.append("Envisager une semaine allégée prochainement.")
    elif tsb > 5:
        if ramp_rate < 0:
            recommendations.append("Fenêtre favorable pour remonter progressivement la charge.")
            recommendations.append("Ajouter du volume ou une séance qualitative si le contexte le permet.")
        else:
            recommendations.append("Bon niveau de fraîcheur pour une séance clé ou une compétition.")
            recommendations.append("Capacité probable à encaisser du travail soutenu.")
    else:
        recommendations.append("Poursuivre l'approche actuelle avec alternance charge/récupération.")
        recommendations.append("Maintenir l'équilibre entre séances dures et jours faciles.")

    return recommendations


def normalize_fitness_summary_from_wellness(
    athlete_name: str,
    wellness_record: Dict[str, Any],
) -> Dict[str, Any]:
    ctl = _first_not_none(
        wellness_record.get("ctl"),
        wellness_record.get("ctLoad"),
        wellness_record.get("ctl_load"),
    )
    atl = _first_not_none(
        wellness_record.get("atl"),
        wellness_record.get("atlLoad"),
        wellness_record.get("atl_load"),
    )
    tsb = _first_not_none(
        wellness_record.get("tsb"),
        wellness_record.get("form"),
    )
    ramp_rate = _first_not_none(
        wellness_record.get("ramp_rate"),
        wellness_record.get("rampRate"),
    )

    fitness_metrics: Dict[str, Any] = {}

    if ctl is not None:
        fitness_metrics["ctl"] = {
            "value": _round_if_number(ctl, 1),
            "description": "Chronic Training Load",
            "explanation": "Charge chronique, reflet approximatif du niveau de fitness.",
        }

    if atl is not None:
        fitness_metrics["atl"] = {
            "value": _round_if_number(atl, 1),
            "description": "Acute Training Load",
            "explanation": "Charge aiguë, reflet approximatif de la fatigue récente.",
        }

    if tsb is not None:
        fitness_metrics["tsb"] = {
            "value": _round_if_number(tsb, 1),
            "description": "Training Stress Balance",
            "explanation": "Équilibre entre fitness et fatigue, souvent utilisé comme indicateur de forme.",
        }

    if ramp_rate is not None:
        fitness_metrics["ramp_rate"] = {
            "value": _round_if_number(ramp_rate, 1),
            "description": "Ramp rate",
            "explanation": "Vitesse d'évolution de la charge chronique.",
        }

    analysis: Dict[str, Any] = {}
    analysis.update(build_form_analysis(tsb))
    analysis.update(build_ramp_rate_analysis(ramp_rate))

    recommendations = build_training_recommendations(tsb, ramp_rate)
    if recommendations:
        analysis["recommendations"] = recommendations

    return {
        "athlete_name": athlete_name,
        "date": wellness_record.get("id") or wellness_record.get("date"),
        "fitness_metrics": fitness_metrics,
        "analysis": analysis,
        "raw_wellness_json": wellness_record,
    }


@router.get(
    "/athlete/fitness",
    operation_id="get_fitness_summary",
    tags=["athlete"],
    summary="Get fitness summary",
    description="Retourne un résumé interprété des métriques CTL, ATL, TSB et ramp rate à partir du dernier enregistrement wellness.",
)
async def get_fitness_summary():
    athlete = await intervals_get(f"/athlete/{INTERVALS_ATHLETE_ID}")
    athlete_name = "Athlete"
    if isinstance(athlete, dict):
        athlete_name = athlete.get("name") or athlete.get("fullname") or "Athlete"

    newest = date.today()
    oldest = newest - timedelta(days=14)

    wellness = await intervals_get(
        f"/athlete/{INTERVALS_ATHLETE_ID}/wellness",
        params={
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        },
    )

    wellness_records = wellness if isinstance(wellness, list) else []
    if not wellness_records:
        return JSONResponse(
            status_code=404,
            content={"detail": "Aucune donnée wellness disponible sur la période récente."},
        )

    wellness_records.sort(
        key=lambda x: str(x.get("id") or x.get("date") or ""),
        reverse=True,
    )

    latest = wellness_records[0]
    result = normalize_fitness_summary_from_wellness(athlete_name, latest)

    if not result.get("fitness_metrics"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Aucune métrique CTL/ATL/TSB exploitable trouvée dans le dernier enregistrement wellness.",
                "latest_wellness_date": latest.get("id") or latest.get("date"),
                "raw_wellness_json": latest,
            },
        )

    return JSONResponse(content=result)