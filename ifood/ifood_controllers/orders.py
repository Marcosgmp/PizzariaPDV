from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ifood.ifood_services.orders import IfoodOrderService

router = APIRouter(prefix="/orders", tags=["orders"])

order_service = IfoodOrderService()

class CancellationRequest(BaseModel):
    reason_code: str
    reason: Optional[str] = None

class PickupCodeValidation(BaseModel):
    code: str

class NegotiationAction(BaseModel):
    negotiation_id: str

@router.get("/poll")
def poll_events():
    try:
        events = order_service.poll_events()
        return {"total_events": len(events), "events": [e.__dict__ for e in events]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}")
def get_order_details(order_id: str):
    order = order_service.get_order_details(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} nao encontrado.")
    return order.__dict__

@router.post("/{order_id}/confirm")
def confirm_order(order_id: str):
    success = order_service.confirm_order(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao confirmar pedido {order_id}.")
    return {"message": f"Pedido {order_id} confirmado com sucesso!"}

@router.post("/{order_id}/start-preparation")
def start_preparation(order_id: str):
    success = order_service.start_preparation(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar preparo do pedido {order_id}.")
    return {"message": f"Preparo do pedido {order_id} iniciado com sucesso!"}

@router.post("/{order_id}/ready-to-pickup")
def ready_to_pickup(order_id: str):
    success = order_service.ready_to_pickup(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao marcar pedido {order_id} como pronto para retirada.")
    return {"message": f"Pedido {order_id} marcado como pronto para retirada!"}

@router.post("/{order_id}/dispatch")
def dispatch_order(order_id: str):
    success = order_service.dispatch_order(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao despachar pedido {order_id}.")
    return {"message": f"Pedido {order_id} despachado com sucesso!"}

@router.get("/{order_id}/cancellation-reasons")
def get_cancellation_reasons(order_id: str):
    try:
        reasons = order_service.get_cancellation_reasons(order_id)
        if not reasons:
            raise HTTPException(status_code=404, detail=f"Nenhum motivo de cancelamento encontrado para o pedido {order_id}.")
        return {
            "order_id": order_id,
            "total_reasons": len(reasons),
            "reasons": [reason.__dict__ for reason in reasons]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/request-cancellation")
def request_cancellation(order_id: str, request: CancellationRequest):
    try:
        success = order_service.request_cancellation(
            order_id=order_id,
            reason_code=request.reason_code,
            reason=request.reason
        )
        if not success:
            raise HTTPException(status_code=500, detail=f"Erro ao solicitar cancelamento do pedido {order_id}.")
        return {"message": f"Solicitacao de cancelamento do pedido {order_id} enviada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/validate-pickup-code")
def validate_pickup_code(order_id: str, validation: PickupCodeValidation):
    try:
        success = order_service.validate_pickup_code(order_id, validation.code)
        if not success:
            raise HTTPException(status_code=400, detail=f"Codigo de coleta invalido para o pedido {order_id}.")
        return {"message": f"Codigo de coleta validado com sucesso para o pedido {order_id}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}/tracking")
def get_tracking(order_id: str):
    try:
        tracking_info = order_service.get_tracking(order_id)
        if not tracking_info:
            raise HTTPException(status_code=404, detail=f"Informacoes de rastreamento nao disponiveis para o pedido {order_id}.")
        return {
            "order_id": order_id,
            "tracking": tracking_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}/negotiation")
def get_negotiation(order_id: str):
    try:
        negotiation = order_service.get_negotiation(order_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail=f"Nenhuma negociacao encontrada para o pedido {order_id}.")
        return {
            "order_id": order_id,
            "negotiation": negotiation.__dict__
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/negotiation/{negotiation_id}/accept")
def accept_negotiation(order_id: str, negotiation_id: str):
    try:
        success = order_service.accept_negotiation(order_id, negotiation_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Erro ao aceitar negociacao {negotiation_id} do pedido {order_id}.")
        return {"message": f"Negociacao {negotiation_id} aceita com sucesso para o pedido {order_id}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/negotiation/{negotiation_id}/reject")
def reject_negotiation(order_id: str, negotiation_id: str):
    try:
        success = order_service.reject_negotiation(order_id, negotiation_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Erro ao rejeitar negociacao {negotiation_id} do pedido {order_id}.")
        return {"message": f"Negociacao {negotiation_id} rejeitada com sucesso para o pedido {order_id}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, reason: str = "OUT_OF_STOCK"):
    try:
        success = order_service.request_cancellation(
            order_id=order_id,
            reason_code=reason,
            reason=f"Cancelado via endpoint legado: {reason}"
        )
        if not success:
            raise HTTPException(status_code=500, detail=f"Erro ao cancelar pedido {order_id}.")
        return {"message": f"Pedido {order_id} cancelado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def list_processed_orders():
    try:
        processed_orders = list(order_service._processed_orders)
        return {
            "total_processed_orders": len(processed_orders),
            "processed_orders": processed_orders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process/new")
def process_new_orders():
    try:
        new_orders = order_service.process_new_orders()
        return {
            "total_new_orders": len(new_orders),
            "orders": [o.__dict__ for o in new_orders],
            "message": "Pedidos processados com sucesso. Aguardando confirmacao manual."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache/clear")
def clear_cache():
    try:
        order_service._acknowledged_events.clear()
        order_service._processed_orders.clear()
        return {"message": "Cache limpo com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/service")
def service_status():
    try:
        status_info = {
            "service": "iFood Order Service",
            "status": "operational",
            "processed_orders_count": len(order_service._processed_orders),
            "acknowledged_events_count": len(order_service._acknowledged_events),
            "merchant_id": order_service.merchant_id,
            "base_url": order_service.base_url
        }
        return status_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))