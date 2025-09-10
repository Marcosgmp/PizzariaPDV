from sqlalchemy import Column, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id_inventory = Column(Integer, primary_key=True, autoincrement=True)
    id_product = Column(Integer, ForeignKey("products.id_product", ondelete="CASCADE"), nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    expiration_date = Column(Date)

    product = relationship("Product", back_populates="inventory")
