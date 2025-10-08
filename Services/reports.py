from sqlalchemy.orm import Session
from Models.orders import Order
from Models.order_items import OrderItem
from Models.products import Product
from Models.payments import Payment
from decimal import Decimal
from datetime import datetime
from typing import List, Dict

def sales_report(db: Session, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Gera relatório de vendas no período.

    Args:
        db (Session): Sessão do SQLAlchemy.
        start_date (datetime): Data inicial.
        end_date (datetime): Data final.

    Returns:
        List[Dict]: Lista com informações de cada pedido.
    """
    orders = db.query(Order).filter(Order.created_at.between(start_date, end_date)).all()
    report = []
    for order in orders:
        items = db.query(OrderItem).filter(OrderItem.id_order == order.id_order).all()
        total_items = sum([item.unit_price * item.quantity for item in items])
        report.append({
            "order_id": order.id_order,
            "customer_id": order.id_customer,
            "total_items": float(total_items),
            "total_order": float(order.total),
            "status": order.status_order
        })
    return report

def inventory_report(db: Session) -> List[Dict]:
    """
    Relatório de estoque atual.

    Args:
        db (Session): Sessão do SQLAlchemy.

    Returns:
        List[Dict]: Lista com produtos e quantidades.
    """
    products = db.query(Product).all()
    return [{
        "product_id": p.id_product,
        "name": p.name,
        "price": float(p.price),
        "stock": p.stock
    } for p in products]

def payments_report(db: Session, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Relatório de pagamentos realizados no período.

    Args:
        db (Session): Sessão do SQLAlchemy.
        start_date (datetime): Data inicial.
        end_date (datetime): Data final.

    Returns:
        List[Dict]: Lista de pagamentos com detalhes.
    """
    payments = db.query(Payment).join(Order).filter(Order.created_at.between(start_date, end_date)).all()
    report = []
    for payment in payments:
        report.append({
            "payment_id": payment.id_payment,
            "order_id": payment.id_order,
            "amount": float(payment.amount),
            "type": payment.type_payment,
            "status": payment.status_payments
        })
    return report
