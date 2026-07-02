from datetime import datetime
from sqlalchemy import Column, Float, String, DateTime, Integer, Numeric, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    
class DeliveryStatus(str, enum.Enum):
    PENDING_ASSIGNMENT = "pending_assignment"
    DRIVER_ASSIGNED = "driver_assigned"
    PICKED_UP = "picked_up"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"

class Order(Base):
    """
    Order model - stores customer orders in business-specific database.

    Each order belongs to a customer and contains multiple order items.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="SET NULL"), nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=True, unique=True)
    coupon_id = Column(Integer, ForeignKey("offers.id", ondelete="SET NULL"), nullable=True)

    # Order number (business-specific, human-readable)
    order_number = Column(String(50), nullable=True, unique=True, index=True)

    # Order totals
    subtotal = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    delivery_charge = Column(Numeric(10, 2), default=0.00, nullable=False)
    total = Column(Numeric(10, 2), default=0.00, nullable=False)

    # Order metadata
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(20), default=OrderStatus.PENDING.value,
                    nullable=False, index=True)
    notes = Column(String(500), nullable=True)

    # Delivery information
    receiver_first_name = Column(String(100), nullable=False)
    receiver_last_name = Column(String(100), nullable=False)
    receiver_email = Column(String(255), nullable=False)
    receiver_phone = Column(String(15), nullable=False)
    # Delivery address if applicable
    # Address information
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default="US")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Delivery distance in miles (for delivery fee calculation)
    delivery_distance = Column(Numeric(10, 2), nullable=True)
    #delivery status
    delivery_status = Column(Enum(DeliveryStatus),
                            default=DeliveryStatus.PENDING_ASSIGNMENT.value, nullable=False)
    
    # Payment information
    payment_intent_id = Column(String(255), nullable=True, index=True)
    # paid, pending, failed, refunded
    payment_status = Column(String(20), nullable=True)
    payment_method = Column(String(50), nullable=True)  # stripe, cash, etc.

    # Order items relationship
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")

    # Customer relationship
    user = relationship("User")
    #cart relationship
    cart = relationship("Cart", back_populates="order")
    #applied combo offers
    applied_combos = relationship("AppliedCombo", back_populates="order")
    #coupon relation
    coupon = relationship("Offer")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)


class OrderItem(Base):
    """
    Order item model - individual items in an order.

    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey(
        "orders.id", ondelete="CASCADE"), nullable=False)
    
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id"),
        nullable=False
    )

    # Item details
    quantity = Column(Integer, nullable=False, default=1)
    # Price at time of order
    unit_price = Column(Numeric(10, 2), nullable=False)
    #quantity * unit_price
    total_price = Column(Numeric(10, 2), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product_variant = relationship("ProductVariant")

class AppliedCombo(Base):
    __tablename__ = "applied_combos"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    combo_offer_id = Column(Integer, ForeignKey("combo_offers.id"), nullable=False)

    quantity_used = Column(Integer, nullable=False, default=1)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    order = relationship("Order", back_populates="applied_combos")
    combo_offer = relationship("ComboOffer")
