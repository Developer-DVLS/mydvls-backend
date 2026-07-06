import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Numeric,
    func,
    JSON,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base



class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)

    global_type = Column(String(255), nullable=False)
    badge = Column(String(255), nullable=True)
    
    title = Column(String(255), nullable=False)
    sub_title = Column(Text, nullable=True)
    
    bottom_card = Column(JSON, nullable=True)
    
    #relationships
    plans = relationship(
        "SubscriptionPlan",
        back_populates="service",
        cascade="all, delete-orphan",
        order_by="SubscriptionPlan.sort_order"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    
    service_id = Column(
        Integer,
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)

    description = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)

    # Trial, deafult= 0 , if 0 then no trial allowed.
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
    
    is_normal = Column(Boolean, default=False, nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    #relationship
    service = relationship("Service",back_populates="plans")
    prices = relationship("SubscriptionPlanPrice",back_populates="plan",cascade="all, delete-orphan")
    addons = relationship("SubscriptionPlanAddon",back_populates="plan",cascade="all, delete-orphan")
    creator = relationship("User",foreign_keys=[created_by])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    


class SubscriptionPlanPrice(Base):
    __tablename__ = "subscription_plan_prices"
    
    __table_args__ = (
        UniqueConstraint(
            "subscription_plan_id",
            "billing_period",
            name="uq_plan_billing_period"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    subscription_plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        index=True
    )
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=False)

    # Billing cycle
    billing_period = Column(String(50), nullable=False)  # monthly, yearly
    
    #relationship
    plan = relationship("SubscriptionPlan",back_populates="prices")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

class SubscriptionPlanAddon(Base):
    __tablename__ = "subscription_plan_addons"

    id = Column(Integer, primary_key=True, index=True)
    
    subscription_plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        index=True
    )
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    #relationship
    plan = relationship("SubscriptionPlan",back_populates="addons")
    prices = relationship(
        "SubscriptionPlanAddonPrice",
        back_populates="addon",
        cascade="all, delete-orphan"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
class SubscriptionPlanAddonPrice(Base):
    __tablename__ = "subscription_plan_addon_prices"

    __table_args__ = (
        UniqueConstraint(
            "subscription_plan_addon_id",
            "billing_period",
            name="uq_addon_billing_period"
        ),
    )

    id = Column(Integer, primary_key=True)

    subscription_plan_addon_id = Column(
        Integer,
        ForeignKey("subscription_plan_addons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    billing_period = Column(String(50), nullable=False)  # monthly, yearly
    price = Column(Numeric(10, 2), nullable=False)

    addon = relationship(
        "SubscriptionPlanAddon",
        back_populates="prices"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )