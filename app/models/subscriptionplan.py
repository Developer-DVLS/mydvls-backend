from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Numeric,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    key = Column(String(255), unique=True, nullable=False)

    description = Column(Text, nullable=True)

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)

    # Billing cycle
    billing_period = Column(String(50), nullable=False)  # monthly, yearly

    # Trial
    trial_days = Column(Integer, default=0)

    # Display
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Limits
    max_users = Column(Integer, nullable=True)
    max_locations = Column(Integer, nullable=True)
    max_products = Column(Integer, nullable=True)

    # Sorting
    sort_order = Column(Integer, default=0)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    creator = relationship(
        "User",
        foreign_keys=[created_by]
    )