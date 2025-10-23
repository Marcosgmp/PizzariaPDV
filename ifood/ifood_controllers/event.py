from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from  ifood_services.event import IfoodEventService

router = APIRouter(prefix="/events", tags=["events"])
event_service = IfoodEventService()

@router.get("/polling")
def get_events(
    merchant_ids: Optional[List[str]] = Query(None, alias="merchants"),
    types: Optional[str] = None,
    groups: Optional[str] = None,
    categories: Optional[str] = None
):
    """
    Obtém novos eventos de pedidos do iFood.
    """
    events = event_service.get_events(merchant_ids, types, groups, categories)
    if events is None:
        raise HTTPException(status_code=500, detail="Erro ao buscar eventos.")
    return events


@router.post("/acknowledgment")
def acknowledge_events(event_ids: List[str]):
    """
    Confirma o recebimento dos eventos (acknowledgment).
    """
    result = event_service.acknowledge_events(event_ids)
    if result is None:
        raise HTTPException(status_code=500, detail="Erro ao confirmar eventos.")
    return result
