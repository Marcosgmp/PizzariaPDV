from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import relationship
from .base import Base

class Product(Base):
    __tablename__ = "products"

    id_product = Column(Integer, primary_key=True, autoincrement=True)
    name_product = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    size_product = Column(String(10))
    price = Column(Numeric(10,2), nullable=False)

    inventory = relationship("Inventory", back_populates="product", uselist=False)
    order_items = relationship("OrderItem", back_populates="product")
