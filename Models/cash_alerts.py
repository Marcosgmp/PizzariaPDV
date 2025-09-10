from sqlalchemy import Column, Integer, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum

class AlertStatus(enum.Enum):
    ativo = "ativo"
    resolvido = "resolvido"

class CashAlert(Base):
    __tablename__ = "cash_alerts"

    id_alert = Column(Integer, primary_key=True, autoincrement=True)
    id_order = Column(Integer, ForeignKey("orders.id_order", ondelete="CASCADE"), nullable=False)
    message_alert = Column(Text, nullable=False)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ativo)

    order = relationship("Order", back_populates="alerts")
