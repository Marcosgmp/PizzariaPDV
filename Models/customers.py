from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, Date, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Customer(Base):
    __tablename__ = "customers"

    id_customer = Column(Integer, primary_key=True)
    name_customers = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    address = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)
    loyalty_points = Column(Integer, default=0)
    latitude = Column(Numeric(9,6))
    longitude = Column(Numeric(9,6))

    orders = relationship("Order", back_populates="customer")
