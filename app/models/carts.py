import enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, Numeric, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

from app.core.database import Base

class CartStatus(str, enum.Enum):
    ACTIVE = "active"
    ORDERED = "ordered"

class Cart(Base):
    """ 
    Cart Model
    
    A user can have only one active cart. Once order is placed, cart status is updated to ordered.
    """
    
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    status =  Column(Enum(CartStatus), default=CartStatus.ACTIVE, nullable=False, index=True)
    
    # relationships
    cart_products = relationship("CartProduct", back_populates="cart", cascade="all, delete-orphan")
    user = relationship("User")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class CartProduct(Base):
    """ 
    Cart Product Model
    """
    
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False, index=True)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"),nullable=False,index=True)
    
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # relationships
    cart = relationship("Cart", back_populates="cart_products")
    product_variant = relationship("ProductVariant")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)