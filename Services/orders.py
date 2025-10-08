from sqlalchemy.orm import Session, joinedload
from Models.orders import Order, OrderStatus
from Models.order_items import OrderItem
from Models.payments import Payment, PaymentStatus
from Models.cash_alerts import CashAlert
from decimal import Decimal
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def create_order(db: Session, customer_id: int, items: List[Dict], payment_method: str) -> Order:
    """
    Cria um pedido com itens e registra o pagamento inicial.
    Valida estoque antes de criar os itens.
    
    Args:
        db: Sessão do banco de dados
        customer_id: ID do cliente
        items: Lista de dicts [{'id_product': int, 'quantity': int, 'note': str, 'price': str, 'alert': bool}, ...]
        payment_method: Tipo de pagamento inicial (DINHEIRO, CARTAO, PIX, etc.)
    
    Returns:
        Pedido criado (Order)
    
    Raises:
        ValueError: Se algum dado estiver incorreto, estoque insuficiente ou pedido não puder ser criado
    """
    try:
        # Valida estoque primeiro
        for item in items:
            if not check_stock_available(db, item['id_product'], item['quantity']):
                product_name = get_product_name(db, item['id_product'])
                raise ValueError(f"Estoque insuficiente para {product_name} (ID: {item['id_product']})")
        
        order = Order(
            id_customer=customer_id,
            status_order=OrderStatus.RECEBIDO,
            total=Decimal('0.00'),
            payment_method=payment_method
        )
        db.add(order)
        db.flush()

        total = Decimal('0.00')
        for item in items:
            unit_price = Decimal(item.get('price', '0.00'))
            order_item = OrderItem(
                id_order=order.id_order,
                id_product=item['id_product'],
                quantity=item['quantity'],
                note=item.get('note', ''),
                unit_price=unit_price
            )
            db.add(order_item)

            total += unit_price * item['quantity']

            # Alerta para itens especiais
            if item.get('alert', False):
                product_name = get_product_name(db, item['id_product'])
                create_cash_alert(
                    db, 
                    order.id_order, 
                    f"ITEM ESPECIAL: {product_name} - {item.get('note', 'Sem observações')}"
                )

        order.total = total

        # Cria pagamento inicial
        payment = Payment(
            id_order=order.id_order,
            type_payment=payment_method,
            amount=total,
            status_payments=PaymentStatus.PENDENTE
        )
        db.add(payment)

        db.commit()
        db.refresh(order)
        logger.info(f"Pedido {order.id_order} criado com sucesso para o cliente {customer_id}")
        return order

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar pedido: {e}")
        raise

def update_order_status(db: Session, order_id: int, new_status: OrderStatus, 
                        alert_message: Optional[str] = None) -> Order:
    """
    Atualiza o status do pedido com validação de transições.
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        raise ValueError("Pedido não encontrado")
    
    # Valida transições de status
    valid_transitions = {
        OrderStatus.RECEBIDO: [OrderStatus.PREPARANDO, OrderStatus.CANCELADO],
        OrderStatus.PREPARANDO: [OrderStatus.A_CAMINHO, OrderStatus.CANCELADO],
        OrderStatus.A_CAMINHO: [OrderStatus.ENTREGUE],
        OrderStatus.ENTREGUE: [],
        OrderStatus.CANCELADO: []
    }
    
    if new_status not in valid_transitions[order.status_order]:
        raise ValueError(f"Transição inválida: {order.status_order.value} → {new_status.value}")

    old_status = order.status_order
    order.status_order = new_status
    db.commit()
    db.refresh(order)

    if alert_message:
        create_cash_alert(db, order_id, f"STATUS ALTERADO: {alert_message}")
    
    logger.info(f"Status do pedido {order_id} alterado: {old_status.value} → {new_status.value}")
    return order

def add_item_to_order(db: Session, order_id: int, item_data: Dict) -> Order:
    """
    Adiciona um item a um pedido existente.
    Valida estoque e status do pedido.
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        raise ValueError("Pedido não encontrado")

    if order.status_order not in [OrderStatus.RECEBIDO, OrderStatus.PREPARANDO]:
        raise ValueError("Não é possível adicionar itens a pedidos em estágio avançado")

    # Valida estoque
    if not check_stock_available(db, item_data['id_product'], item_data['quantity']):
        product_name = get_product_name(db, item_data['id_product'])
        raise ValueError(f"Estoque insuficiente para {product_name}")

    unit_price = Decimal(item_data.get('price', '0.00'))
    new_item = OrderItem(
        id_order=order.id_order,
        id_product=item_data['id_product'],
        quantity=item_data['quantity'],
        note=item_data.get('note', ''),
        unit_price=unit_price
    )
    db.add(new_item)
    order.total += unit_price * item_data['quantity']

    # Atualiza pagamento
    payment = db.query(Payment).filter(Payment.id_order == order_id).first()
    if payment:
        payment.amount = order.total

    # Alerta para itens adicionais
    if item_data.get('alert', False):
        product_name = get_product_name(db, item_data['id_product'])
        create_cash_alert(
            db, 
            order.id_order, 
            f"ITEM ADICIONADO: {product_name} - {item_data.get('note', '')}"
        )

    db.commit()
    db.refresh(order)
    logger.info(f"Item adicionado ao pedido {order_id}: {item_data}")
    return order

def get_orders_by_customer(db: Session, customer_id: int) -> List[Order]:
    """Retorna todos os pedidos de um cliente"""
    return db.query(Order).filter(Order.id_customer == customer_id).order_by(Order.created_at.desc()).all()

def get_order_with_details(db: Session, order_id: int) -> Optional[Order]:
    """Retorna pedido com todos os detalhes (customer, items, payments, driver, alerts)"""
    return db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.payments),
        joinedload(Order.driver),
        joinedload(Order.alerts)
    ).filter(Order.id_order == order_id).first()

def get_orders_by_status(db: Session, status: OrderStatus, limit: int = 100) -> List[Order]:
    """Retorna pedidos por status"""
    return db.query(Order).filter(Order.status_order == status).order_by(Order.created_at.desc()).limit(limit).all()

def get_active_orders(db: Session) -> List[Order]:
    """Retorna pedidos ativos (não entregues ou cancelados)"""
    return db.query(Order).filter(
        Order.status_order.in_([OrderStatus.RECEBIDO, OrderStatus.PREPARANDO, OrderStatus.A_CAMINHO])
    ).order_by(Order.created_at.asc()).all()

def cancel_order(db: Session, order_id: int, reason: str = "") -> Order:
    """
    Cancela pedido e estorna pagamento se necessário.
    
    Args:
        db: Sessão do banco
        order_id: ID do pedido
        reason: Motivo do cancelamento
    
    Returns:
        Pedido cancelado
    
    Raises:
        ValueError: Se pedido não encontrado ou já entregue
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        raise ValueError("Pedido não encontrado")
    
    if order.status_order == OrderStatus.ENTREGUE:
        raise ValueError("Não é possível cancelar pedido já entregue")
    
    old_status = order.status_order
    order.status_order = OrderStatus.CANCELADO
    
    # Cancela pagamento se existir e estiver confirmado
    payment = db.query(Payment).filter(Payment.id_order == order_id).first()
    if payment and payment.status_payments == PaymentStatus.CONFIRMADO:
        payment.status_payments = PaymentStatus.CANCELADO
        logger.info(f"Pagamento {payment.id_payment} cancelado junto com o pedido {order_id}")
    
    # Cria alerta de cancelamento
    alert_msg = f"PEDIDO CANCELADO: {reason}" if reason else "Pedido cancelado pelo sistema"
    create_cash_alert(db, order_id, alert_msg)
    
    db.commit()
    db.refresh(order)
    logger.info(f"Pedido {order_id} cancelado. Status anterior: {old_status.value}. Motivo: {reason}")
    return order

def create_cash_alert(db: Session, order_id: int, message: str) -> CashAlert:
    """Cria alerta de caixa"""
    alert = CashAlert(
        id_order=order_id,
        message_alert=message,
        status='ATIVO'
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info(f"Alerta criado para pedido {order_id}: {message}")
    return alert

def check_stock_available(db: Session, product_id: int, quantity: int) -> bool:
    """Verifica se há estoque suficiente para o produto"""
    from Models.inventory import Inventory
    inventory = db.query(Inventory).filter(Inventory.id_product == product_id).first()
    return inventory and inventory.stock_quantity >= quantity

def get_product_name(db: Session, product_id: int) -> str:
    """Retorna nome do produto pelo ID"""
    from Models.products import Product
    product = db.query(Product).filter(Product.id_product == product_id).first()
    return product.name_product if product else "Produto Desconhecido"