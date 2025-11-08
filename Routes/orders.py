from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from Models.orders import Order, OrderStatus
from Models.order_items import OrderItem
from Models.customers import Customer
from Models.products import Product
from Services.order_service import OrderService
from database import get_db
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["orders"])

# Schemas para requests/responses
class OrderItemCreate(BaseModel):
    id_product: int
    quantity: int
    note: Optional[str] = None

class OrderCreate(BaseModel):
    id_customer: int
    items: List[OrderItemCreate]
    payment_method: str
    id_driver: Optional[int] = None

class OrderResponse(BaseModel):
    id_order: int
    id_customer: int
    id_driver: Optional[int]
    order_date: datetime
    status_order: str
    total: float
    payment_method: str
    customer_name: str
    items: List[dict]

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status_order: OrderStatus

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """
    Cria um novo pedido
    """
    try:
        order_service = OrderService(db)
        new_order = order_service.create_order(order_data)
        return new_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Busca um pedido específico pelo ID
    """
    try:
        order_service = OrderService(db)
        order = order_service.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.patch("/{order_id}/status")
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    """
    Atualiza o status de um pedido
    """
    try:
        order_service = OrderService(db)
        updated_order = order_service.update_order_status(order_id, status_update.status_order)
        if not updated_order:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        return {"message": "Status atualizado com sucesso", "order": updated_order}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/", response_model=List[OrderResponse])
def get_daily_orders(
    db: Session = Depends(get_db),
    date: Optional[str] = None,
    status: Optional[OrderStatus] = None
):
    """
    Lista pedidos do dia (ou por data específica)
    """
    try:
        order_service = OrderService(db)
        orders = order_service.get_daily_orders(date, status)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")