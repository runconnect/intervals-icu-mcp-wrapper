"""Event/calendar management routes for Intervals.icu MCP wrapper."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.client import INTERVALS_ATHLETE_ID, intervals_get, intervals_post, intervals_put, intervals_delete

router = APIRouter()

VALID_CATEGORIES = ["WORKOUT", "NOTE", "RACE", "GOAL"]


# ---------------------------------------------------------------------------
# Pydantic models (corps des requêtes POST / PUT)
# ---------------------------------------------------------------------------

class EventCreateBody(BaseModel):
    start_date_local: str
    name: str
    category: str
    description: Optional[str] = None
    type: Optional[str] = None
    moving_time: Optional[int] = None
    distance: Optional[float] = None
    icu_training_load: Optional[int] = None

class EventUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date_local: Optional[str] = None
    type: Optional[str] = None
    moving_time: Optional[int] = None
    distance: Optional[float] = None
    icu_training_load: Optional[int] = None

class BulkCreateBody(BaseModel):
    events: List[Dict[str, Any]]

class BulkDeleteBody(BaseModel):
    event_ids: List[int]

class DuplicateBody(BaseModel):
    new_date: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": event.get("id"),
        "start_date": event.get("start_date_local") or event.get("start_date"),
        "name": event.get("name"),
        "category": event.get("category"),
    }
    if event.get("description"):
        result["description"] = event["description"]
    if event.get("type"):
        result["type"] = event["type"]
    if event.get("moving_time") is not None:
        result["duration_seconds"] = event["moving_time"]
    if event.get("distance") is not None:
        result["distance_meters"] = event["distance"]
    if event.get("icu_training_load") is not None:
        result["training_load"] = event["icu_training_load"]
    return result

def _validate_date(date_str: str, field: str = "start_date_local") -> None:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Format de date invalide pour '{field}'. Utiliser YYYY-MM-DD.",
        )

def _validate_category(category: str) -> str:
    cat = category.upper()
    if cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Catégorie invalide. Valeurs autorisées : {', '.join(VALID_CATEGORIES)}",
        )
    return cat


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------

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
    events = data if isinstance(data, list) else []
    normalized = [_normalize_event(e) for e in events]
    return JSONResponse(content={"count": len(normalized), "events": normalized})


# ---------------------------------------------------------------------------
# POST /events
# ---------------------------------------------------------------------------

@router.post(
    "/events",
    operation_id="create_event",
    tags=["intervals"],
    summary="Create a calendar event",
    description=(
        "Crée un nouvel événement calendrier (WORKOUT, NOTE, RACE ou GOAL). "
        "Les champs optionnels type, moving_time, distance et icu_training_load "
        "s'appliquent principalement aux événements de type WORKOUT."
    ),
)
async def create_event(body: EventCreateBody):
    _validate_date(body.start_date_local)
    category = _validate_category(body.category)

    payload: Dict[str, Any] = {
        "start_date_local": body.start_date_local,
        "name": body.name,
        "category": category,
    }
    if body.description is not None:
        payload["description"] = body.description
    if body.type is not None:
        payload["type"] = body.type
    if body.moving_time is not None:
        payload["moving_time"] = body.moving_time
    if body.distance is not None:
        payload["distance"] = body.distance
    if body.icu_training_load is not None:
        payload["icu_training_load"] = body.icu_training_load

    data = await intervals_post(
        f"/athlete/{INTERVALS_ATHLETE_ID}/events",
        json=payload,
    )
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Réponse inattendue de l'API Intervals.icu")

    return JSONResponse(
        status_code=201,
        content={"message": f"Événement '{body.name}' créé avec succès.", "event": _normalize_event(data)},
    )


# ---------------------------------------------------------------------------
# PUT /events/{event_id}
# ---------------------------------------------------------------------------

@router.put(
    "/events/{event_id}",
    operation_id="update_event",
    tags=["intervals"],
    summary="Update a calendar event",
    description="Modifie un ou plusieurs champs d'un événement existant. Seuls les champs fournis sont mis à jour.",
)
async def update_event(event_id: int, body: EventUpdateBody):
    payload: Dict[str, Any] = {}
    if body.name is not None:
        payload["name"] = body.name
    if body.description is not None:
        payload["description"] = body.description
    if body.start_date_local is not None:
        _validate_date(body.start_date_local, "start_date_local")
        payload["start_date_local"] = body.start_date_local
    if body.type is not None:
        payload["type"] = body.type
    if body.moving_time is not None:
        payload["moving_time"] = body.moving_time
    if body.distance is not None:
        payload["distance"] = body.distance
    if body.icu_training_load is not None:
        payload["icu_training_load"] = body.icu_training_load

    if not payload:
        raise HTTPException(status_code=400, detail="Aucun champ fourni. Spécifiez au moins un champ à modifier.")

    data = await intervals_put(
        f"/athlete/{INTERVALS_ATHLETE_ID}/events/{event_id}",
        json=payload,
    )
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Réponse inattendue de l'API Intervals.icu")

    return JSONResponse(content={"message": f"Événement {event_id} mis à jour.", "event": _normalize_event(data)})


# ---------------------------------------------------------------------------
# DELETE /events/{event_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/events/{event_id}",
    operation_id="delete_event",
    tags=["intervals"],
    summary="Delete a calendar event",
    description="Supprime définitivement un événement du calendrier. Cette action est irréversible.",
)
async def delete_event(event_id: int):
    await intervals_delete(f"/athlete/{INTERVALS_ATHLETE_ID}/events/{event_id}")
    return JSONResponse(content={"message": f"Événement {event_id} supprimé.", "event_id": event_id, "deleted": True})


# ---------------------------------------------------------------------------
# POST /events/bulk
# ---------------------------------------------------------------------------

@router.post(
    "/events/bulk",
    operation_id="bulk_create_events",
    tags=["intervals"],
    summary="Bulk create calendar events",
    description="Crée plusieurs événements en une seule opération. Chaque objet doit contenir start_date_local, name et category.",
)
async def bulk_create_events(body: BulkCreateBody):
    if not body.events:
        raise HTTPException(status_code=400, detail="La liste d'événements ne peut pas être vide.")

    for i, evt in enumerate(body.events):
        for field in ("start_date_local", "name", "category"):
            if field not in evt:
                raise HTTPException(status_code=400, detail=f"Événement {i} : champ '{field}' manquant.")
        _validate_date(evt["start_date_local"], f"events[{i}].start_date_local")
        evt["category"] = _validate_category(evt["category"])

    data = await intervals_post(f"/athlete/{INTERVALS_ATHLETE_ID}/events/bulk", json=body.events)
    created = data if isinstance(data, list) else []
    normalized = [_normalize_event(e) for e in created]

    return JSONResponse(
        status_code=201,
        content={"message": f"{len(normalized)} événement(s) créé(s).", "count": len(normalized), "events": normalized},
    )


# ---------------------------------------------------------------------------
# DELETE /events/bulk
# ---------------------------------------------------------------------------

@router.delete(
    "/events/bulk",
    operation_id="bulk_delete_events",
    tags=["intervals"],
    summary="Bulk delete calendar events",
    description="Supprime plusieurs événements en une seule opération à partir d'une liste d'identifiants.",
)
async def bulk_delete_events(body: BulkDeleteBody):
    if not body.event_ids:
        raise HTTPException(status_code=400, detail="La liste d'identifiants ne peut pas être vide.")

    await intervals_delete(f"/athlete/{INTERVALS_ATHLETE_ID}/events/bulk", json=body.event_ids)
    return JSONResponse(content={"message": f"{len(body.event_ids)} événement(s) supprimé(s).", "deleted_count": len(body.event_ids), "event_ids": body.event_ids})


# ---------------------------------------------------------------------------
# POST /events/{event_id}/duplicate
# ---------------------------------------------------------------------------

@router.post(
    "/events/{event_id}/duplicate",
    operation_id="duplicate_event",
    tags=["intervals"],
    summary="Duplicate a calendar event",
    description="Crée une copie d'un événement existant à une nouvelle date en conservant toutes ses propriétés.",
)
async def duplicate_event(event_id: int, body: DuplicateBody):
    _validate_date(body.new_date, "new_date")

    data = await intervals_post(
        f"/athlete/{INTERVALS_ATHLETE_ID}/events/{event_id}/duplicate",
        json={"start_date_local": body.new_date},
    )
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Réponse inattendue de l'API Intervals.icu")

    return JSONResponse(
        status_code=201,
        content={"message": f"Événement {event_id} dupliqué vers {body.new_date}.", "original_event_id": event_id, "event": _normalize_event(data)},
    )