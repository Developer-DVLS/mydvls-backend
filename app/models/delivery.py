from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class DeliveryConfig(Base):
    """
    Delivery configuration model - stores distance-based delivery pricing.

    Multiple delivery pricing tiers based on distance ranges.
    Example: 0-5km = $7, 5-7km = $10, 7-10km = $15, etc.
    """
    __tablename__ = "delivery_configs"

    id = Column(Integer, primary_key=True)

    # Distance range (in miles)
    # Minimum distance in miles
    min_distance = Column(Numeric(10, 2), nullable=False)
    # Maximum distance (NULL = unlimited)
    max_distance = Column(Numeric(10, 2), nullable=True)

    # Pricing
    # Delivery fee for this range
    delivery_fee = Column(Numeric(10, 2), nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint('min_distance >= 0',
                        name='check_min_distance_positive'),
        CheckConstraint('max_distance IS NULL OR max_distance > min_distance',
                        name='check_max_greater_than_min'),
        CheckConstraint('delivery_fee >= 0',
                        name='check_delivery_fee_positive'),
    )

    def __repr__(self):
        max_dist = f"{self.max_distance}km" if self.max_distance else "∞"
        return f"<DeliveryConfig({self.min_distance}km - {max_dist}: ${self.delivery_fee})>"
