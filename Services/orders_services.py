from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from Models.orders import Order, OrderStatus
from Models.order_items import OrderItem
from Models.customers import Customer
from Models.products import Product
from Models.inventory import Inventory
from Models.payments import Payment, PaymentStatus
from typing import List, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, order_data) -> Order:
        """
        Cria um novo pedido com cálculo automático do total
        """
        # Verifica se o cliente existe
        customer = self.db.query(Customer).filter(Customer.id_customer == order_data.id_customer).first()
        if not customer:
            raise ValueError("Cliente não encontrado")

        # Calcula o total do pedido
        total_amount = 0
        order_items = []

        for item in order_data.items:
            product = self.db.query(Product).filter(Product.id_product == item.id_product).first()
            if not product:
                raise ValueError(f"Produto ID {item.id_product} não encontrado")
            
            # Verifica estoque
            inventory = self.db.query(Inventory).filter(Inventory.id_product == item.id_product).first()
            if inventory and inventory.stock_quantity < item.quantity:
                raise ValueError(f"Estoque insuficiente para {product.name_product}")
            
            total_amount += float(product.price) * item.quantity
            
            # Prepara itens do pedido
            order_item = OrderItem(
                id_product=item.id_product,
                quantity=item.quantity,
                note=item.note
            )
            order_items.append(order_item)

        # Cria o pedido
        new_order = Order(
            id_customer=order_data.id_customer,
            id_driver=order_data.id_driver,
            total=total_amount,
            payment_method=order_data.payment_method,
            status_order=OrderStatus.preparando,
            items=order_items
        )

        self.db.add(new_order)
        self.db.flush()  # Para obter o ID do pedido

        # Cria registro de pagamento
        payment = Payment(
            id_order=new_order.id_order,
            type_payment=order_data.payment_method,
            status_payments=PaymentStatus.pendente
        )
        self.db.add(payment)

        # Atualiza estoque
        self._update_inventory(order_data.items)

        self.db.commit()
        self.db.refresh(new_order)

        logger.info(f"Pedido {new_order.id_order} criado com total R$ {total_amount}")
        return new_order

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """
        Busca um pedido pelo ID com informações relacionadas
        """
        order = self.db.query(Order).filter(Order.id_order == order_id).first()
        if order:
            # Carrega relações
            self.db.refresh(order, ['customer', 'items', 'items.product', 'driver'])
        return order

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> Optional[Order]:
        """
        Atualiza o status de um pedido
        """
        order = self.db.query(Order).filter(Order.id_order == order_id).first()
        if not order:
            return None

        order.status_order = new_status
        order.order_date = datetime.utcnow()

        # Se o pedido foi entregue, marca pagamento como confirmado
        if new_status == OrderStatus.entregue:
            payment = self.db.query(Payment).filter(Payment.id_order == order_id).first()
            if payment:
                payment.status_payments = PaymentStatus.confirmado

        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Status do pedido {order_id} atualizado para {new_status}")
        return order

    def get_daily_orders(self, target_date: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        Lista pedidos do dia (ou data específica) com filtro opcional por status
        """
        query = self.db.query(Order)
        
        # Filtra por data
        if target_date:
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                query = query.filter(func.date(Order.order_date) == target_date)
            except ValueError:
                raise ValueError("Formato de data inválido. Use YYYY-MM-DD")
        else:
            # Data atual por padrão
            today = date.today()
            query = query.filter(func.date(Order.order_date) == today)

        # Filtra por status se fornecido
        if status:
            query = query.filter(Order.status_order == status)

        orders = query.order_by(Order.order_date.desc()).all()
        
        # Carrega relações
        for order in orders:
            self.db.refresh(order, ['customer', 'items', 'items.product'])

        return orders

    def _update_inventory(self, items: List) -> None:
        """
        Atualiza o estoque dos produtos vendidos
        """
        for item in items:
            inventory = self.db.query(Inventory).filter(Inventory.id_product == item.id_product).first()
            if inventory:
                inventory.stock_quantity -= item.quantity
                logger.info(f"Estoque do produto {item.id_product} atualizado: -{item.quantity}")

    def cancel_order(self, order_id: int) -> Optional[Order]:
        """
        Cancela um pedido e reverte o estoque
        """
        order = self.db.query(Order).filter(Order.id_order == order_id).first()
        if not order:
            return None

        if order.status_order == OrderStatus.entregue:
            raise ValueError("Não é possível cancelar um pedido já entregue")

        # Reverte estoque
        for item in order.items:
            inventory = self.db.query(Inventory).filter(Inventory.id_product == item.id_product).first()
            if inventory:
                inventory.stock_quantity += item.quantity

        # Atualiza status
        order.status_order = OrderStatus.cancelado
        
        # Cancela pagamento
        payment = self.db.query(Payment).filter(Payment.id_order == order_id).first()
        if payment:
            payment.status_payments = PaymentStatus.cancelado

        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Pedido {order_id} cancelado")
        return order