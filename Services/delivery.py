from sqlalchemy.orm import Session
from Models.orders import Order
from Models.drivers import Driver
from typing import Optional

def assign_driver(db: Session, order_id: int, driver_id: int) -> Order:
    """
    Atribui um motorista a um pedido.

    Args:
        db (Session): Sessão do SQLAlchemy.
        order_id (int): ID do pedido.
        driver_id (int): ID do motorista.

    Returns:
        Order: Pedido atualizado com o motorista atribuído.

    Raises:
        ValueError: Caso o pedido ou o motorista não seja encontrado.
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    driver = db.query(Driver).filter(Driver.id_driver == driver_id).first()

    if not order:
        raise ValueError("Pedido não encontrado")
    if not driver:
        raise ValueError("Motorista não encontrado")

    order.driver_id = driver.id_driver
    order.delivery_status = 'ATRIBUÍDO'
    db.commit()
    db.refresh(order)
    return order

def update_delivery_status(db: Session, order_id: int, status: str) -> Order:
    """
    Atualiza o status de entrega de um pedido.

    Args:
        db (Session): Sessão do SQLAlchemy.
        order_id (int): ID do pedido.
        status (str): Novo status de entrega.

    Returns:
        Order: Pedido com status de entrega atualizado.

    Raises:
        ValueError: Caso o pedido não seja encontrado.
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        raise ValueError("Pedido não encontrado")

    order.delivery_status = status
    db.commit()
    db.refresh(order)
    return order

def get_delivery_info(db: Session, order_id: int) -> Optional[dict]:
    """
    Retorna informações de entrega de um pedido.

    Args:
        db (Session): Sessão do SQLAlchemy.
        order_id (int): ID do pedido.

    Returns:
        dict | None: Informações do pedido ou None se não encontrado.
    """
    order = db.query(Order).filter(Order.id_order == order_id).first()
    if not order:
        return None
    return {
        'order_id': order.id_order,
        'driver_id': order.driver_id,
        'delivery_status': order.delivery_status
    }
