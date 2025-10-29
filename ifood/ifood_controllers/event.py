from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from  ifood_services.event import IfoodEventService

router = APIRouter(prefix="/events", tags=["events"])
event_service = IfoodEventService()

@router.get("/polling")
async def get_events(
    merchant_ids: Optional[List[str]] = Query(None, alias="merchants"),
    types: Optional[str] = None,
    groups: Optional[str] = None,
    categories: Optional[str] = None
):
    """
    Obtém novos eventos do iFood - Endpoint de polling
    """
    try:
        events = event_service.get_events(merchant_ids, types, groups, categories)
        if events is None:
            raise HTTPException(
                status_code=500, 
                detail="Erro ao buscar eventos no iFood"
            )
        return {
            "status": "success",
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/acknowledgment")
async def acknowledge_events(event_ids: List[str]):
    """
    Confirma recebimento de eventos (ACK) - OBRIGATÓRIO
    """
    try:
        result = event_service.acknowledge_events(event_ids)
        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Erro ao confirmar eventos"
            )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )