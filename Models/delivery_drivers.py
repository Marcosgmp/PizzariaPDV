from sqlalchemy import Column, Integer, String, Enum, Numeric
from sqlalchemy.orm import relationship
from .base import Base
import enum

class DriverStatus(enum.Enum):
    disponivel = "Disponível"
    em_entrega = "Em entrega"

class DeliveryDriver(Base):
    __tablename__ = "delivery_drivers"

    id_driver = Column(Integer, primary_key=True, autoincrement=True)
    name_driver = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    status_driver = Column(Enum(DriverStatus), nullable=False, default=DriverStatus.disponivel)
    latitude = Column(Numeric(9,6), nullable=True)
    longitude = Column(Numeric(9,6), nullable=True)

    orders = relationship("Order", back_populates="driver")
