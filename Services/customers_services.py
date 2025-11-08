from sqlalchemy.orm import Session
from sqlalchemy import or_
from Models.customers import Customer
from Models.orders import Order, OrderStatus
from Models.order_items import OrderItem
from Models.products import Product
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def create_customer(self, customer_data) -> Customer:
        """
        Cria um novo cliente
        """
        # Verifica se já existe cliente com o mesmo telefone
        existing_customer = self.db.query(Customer).filter(
            Customer.phone == customer_data.phone
        ).first()
        
        if existing_customer:
            raise ValueError("Já existe um cliente cadastrado com este telefone")

        new_customer = Customer(
            name_customers=customer_data.name_customers,
            phone=customer_data.phone,
            address=customer_data.address,
            latitude=customer_data.latitude,
            longitude=customer_data.longitude
        )

        self.db.add(new_customer)
        self.db.commit()
        self.db.refresh(new_customer)
        
        logger.info(f"Cliente {new_customer.id_customer} criado: {new_customer.name_customers}")
        return new_customer

    def get_customers(self, skip: int = 0, limit: int = 100, phone: Optional[str] = None) -> List[Customer]:
        """
        Lista clientes com filtro opcional por telefone
        """
        query = self.db.query(Customer)
        
        if phone:
            query = query.filter(Customer.phone.contains(phone))
        
        customers = query.offset(skip).limit(limit).all()
        return customers

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        Busca cliente pelo ID
        """
        return self.db.query(Customer).filter(Customer.id_customer == customer_id).first()

    def get_customer_by_phone(self, phone: str) -> Optional[Customer]:
        """
        Busca cliente pelo telefone (útil para delivery)
        """
        return self.db.query(Customer).filter(Customer.phone == phone).first()

    def get_customer_orders(self, customer_id: int) -> List[dict]:
        """
        Retorna o histórico de pedidos de um cliente
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Cliente não encontrado")

        orders = self.db.query(Order).filter(Order.id_customer == customer_id).order_by(
            Order.order_date.desc()
        ).all()

        orders_data = []
        for order in orders:
            # Carrega os itens do pedido
            self.db.refresh(order, ['items', 'items.product'])
            
            order_data = {
                "id_order": order.id_order,
                "order_date": order.order_date,
                "status_order": order.status_order.value,
                "total": float(order.total),
                "payment_method": order.payment_method,
                "items": [
                    {
                        "product_name": item.product.name_product if item.product else "Produto não encontrado",
                        "quantity": item.quantity,
                        "note": item.note
                    }
                    for item in order.items
                ]
            }
            orders_data.append(order_data)

        return orders_data

    def update_customer(self, customer_id: int, customer_data) -> Optional[Customer]:
        """
        Atualiza os dados de um cliente
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return None

        # Atualiza apenas os campos fornecidos
        update_data = customer_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)

        self.db.commit()
        self.db.refresh(customer)
        
        logger.info(f"Cliente {customer_id} atualizado")
        return customer

    def delete_customer(self, customer_id: int) -> bool:
        """
        Exclui um cliente apenas se não tiver pedidos associados
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return False

        # Verifica se o cliente tem pedidos
        has_orders = self.db.query(Order).filter(Order.id_customer == customer_id).first()
        if has_orders:
            raise ValueError("Não é possível excluir cliente com pedidos associados")

        self.db.delete(customer)
        self.db.commit()
        
        logger.info(f"Cliente {customer_id} excluído")
        return True

    def update_loyalty_points(self, customer_id: int, points: int) -> Optional[Customer]:
        """
        Atualiza os pontos de fidelidade do cliente
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return None

        customer.loyalty_points += points
        self.db.commit()
        self.db.refresh(customer)
        
        logger.info(f"Pontos de fidelidade do cliente {customer_id} atualizados: {customer.loyalty_points}")
        return customer