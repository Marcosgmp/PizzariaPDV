from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
import enum

class PaymentStatus(enum.Enum):
    pendente = "Pendente"
    confirmado = "Confirmado"
    cancelado = "Cancelado"

class Payment(Base):
    __tablename__ = "payments"

    id_payment = Column(Integer, primary_key=True, autoincrement=True)
    id_order = Column(Integer, ForeignKey("orders.id_order", ondelete="CASCADE"), unique=True, nullable=False)
    type_payment = Column(String(20), nullable=False)
    status_payments = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pendente)
    payment_date = Column(TIMESTAMP, default=datetime.utcnow)

    order = relationship("Order", back_populates="payments")
