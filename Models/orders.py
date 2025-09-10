from sqlalchemy import Column, Integer, Numeric, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
import enum

class OrderStatus(enum.Enum):
    preparando = "Preparando"
    a_caminho = "A caminho"
    entregue = "Entregue"

class Order(Base):
    __tablename__ = "orders"

    id_order = Column(Integer, primary_key=True, autoincrement=True)
    id_customer = Column(Integer, ForeignKey("customers.id_customer", ondelete="CASCADE"), nullable=False)
    id_driver = Column(Integer, ForeignKey("delivery_drivers.id_driver"))
    order_date = Column(TIMESTAMP, default=datetime.utcnow)
    status_order = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.preparando)
    total = Column(Numeric(10,2), nullable=False)
    payment_method = Column(String(20), nullable=False)

    customer = relationship("Customer", back_populates="orders")
    driver = relationship("DeliveryDriver", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", uselist=False)
    alerts = relationship("CashAlert", back_populates="order", cascade="all, delete-orphan")
