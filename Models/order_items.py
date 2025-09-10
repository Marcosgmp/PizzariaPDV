from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id_item = Column(Integer, primary_key=True, autoincrement=True)
    id_order = Column(Integer, ForeignKey("orders.id_order", ondelete="CASCADE"), nullable=False)
    id_product = Column(Integer, ForeignKey("products.id_product"), nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(Text)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
