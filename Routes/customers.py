from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from Models.customers import Customer
from Models.orders import Order
from Services.customer_service import CustomerService
from database import get_db
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/customers", tags=["customers"])
logger = logging.getLogger(__name__)

# Schemas para requests/responses
class CustomerCreate(BaseModel):
    name_customers: str
    phone: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class CustomerResponse(BaseModel):
    id_customer: int
    name_customers: str
    phone: str
    address: str
    loyalty_points: int
    created_at: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True

class CustomerUpdate(BaseModel):
    name_customers: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(customer_data: CustomerCreate, db: Session = Depends(get_db)):
    """
    Cria um novo cliente
    """
    try:
        customer_service = CustomerService(db)
        new_customer = customer_service.create_customer(customer_data)
        return new_customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao criar cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/", response_model=List[CustomerResponse])
def get_customers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    phone: Optional[str] = None
):
    """
    Lista clientes com possibilidade de filtrar por telefone
    """
    try:
        customer_service = CustomerService(db)
        customers = customer_service.get_customers(skip, limit, phone)
        return customers
    except Exception as e:
        logger.error(f"Erro ao buscar clientes: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """
    Busca um cliente específico pelo ID
    """
    try:
        customer_service = CustomerService(db)
        customer = customer_service.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        return customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/{customer_id}/orders", response_model=List[dict])
def get_customer_orders(customer_id: int, db: Session = Depends(get_db)):
    """
    Busca o histórico de pedidos de um cliente
    """
    try:
        customer_service = CustomerService(db)
        orders = customer_service.get_customer_orders(customer_id)
        return orders
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos do cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, customer_data: CustomerUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um cliente
    """
    try:
        customer_service = CustomerService(db)
        updated_customer = customer_service.update_customer(customer_id, customer_data)
        if not updated_customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        return updated_customer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """
    Exclui um cliente (apenas se não tiver pedidos)
    """
    try:
        customer_service = CustomerService(db)
        success = customer_service.delete_customer(customer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cliente não encontrado ou possui pedidos associados")
        return {"message": "Cliente excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir cliente: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")