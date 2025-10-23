from fastapi import APIRouter, HTTPException
from ifood.ifood_services.orders import IfoodOrderService

router = APIRouter(prefix="/orders", tags=["orders"])

order_service = IfoodOrderService()


@router.get("/poll")
def poll_events():
    """
    Faz polling de eventos do iFood e retorna novos pedidos.
    """
    try:
        events = order_service.poll_events()
        return {"total_events": len(events), "events": [e.__dict__ for e in events]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{order_id}")
def get_order_details(order_id: str):
    """
    Retorna os detalhes de um pedido específico.
    """
    order = order_service.get_order_details(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} não encontrado.")
    return order.__dict__


@router.post("/{order_id}/confirm")
def confirm_order(order_id: str):
    """
    Confirma um pedido.
    """
    success = order_service.confirm_order(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao confirmar pedido {order_id}.")
    return {"message": f"Pedido {order_id} confirmado com sucesso!"}


@router.post("/{order_id}/start-preparation")
def start_preparation(order_id: str):
    """
    Inicia o preparo do pedido.
    """
    success = order_service.start_preparation(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar preparo do pedido {order_id}.")
    return {"message": f"Preparo do pedido {order_id} iniciado com sucesso!"}


@router.post("/{order_id}/ready-to-pickup")
def ready_to_pickup(order_id: str):
    """
    Marca pedido como pronto para retirada (apenas TAKEOUT).
    """
    success = order_service.ready_to_pickup(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao marcar pedido {order_id} como pronto para retirada.")
    return {"message": f"Pedido {order_id} marcado como pronto para retirada!"}


@router.post("/{order_id}/dispatch")
def dispatch_order(order_id: str):
    """
    Despacha o pedido (apenas DELIVERY).
    """
    success = order_service.dispatch_order(order_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao despachar pedido {order_id}.")
    return {"message": f"Pedido {order_id} despachado com sucesso!"}


@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, reason: str = "OUT_OF_STOCK"):
    """
    Cancela um pedido.
    """
    success = order_service.cancel_order(order_id, reason)
    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar pedido {order_id}.")
    return {"message": f"Pedido {order_id} cancelado com sucesso!"}


@router.get("/process")
def process_new_orders():
    """
    Processa novos pedidos automaticamente (polling + confirmação automática).
    """
    try:
        new_orders = order_service.process_new_orders()
        return {
            "total_new_orders": len(new_orders),
            "orders": [o.__dict__ for o in new_orders]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
