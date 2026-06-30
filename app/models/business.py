import enum
from app.core.database import Base

from datetime import datetime
from sqlalchemy import JSON, Column, Enum, Integer, Numeric, String, DateTime, Boolean, ForeignKey, Float, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Basic Details
    legal_business_name = Column(String(255), nullable=False)
    dba_name = Column(String(255), nullable=True)
    owner_name = Column(String(255), nullable=False)

    business_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(30), nullable=False)
    logo = Column(String(500), nullable=True)

    # Description
    business_description = Column(Text, nullable=True)
    website_url = Column(String(500), nullable=True)

    # Operational
    timezone = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True, default="USD")
    language = Column(String(20), nullable=True, default="en")

    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)

    team_size = Column(String(50), nullable=True)

    # Categories
    product_categories = Column(JSON, nullable=True)

    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    #selected template
    template = Column(JSON, nullable=True)
    
    # Address Details
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default="US")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    #legal details
    tax_number = Column(String(100), nullable=True)
    employer_identification_number = Column(String(100), nullable=True)
    business_license_number = Column(String(100), nullable=True)
    insurance_policy_number = Column(String(100), nullable=True)
    vat_number = Column(String(100), nullable=True)
    
    #relationship
    user = relationship("User")
    subscriptions = relationship("BusinessSubscription", back_populates="business", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    
class SubscriptionStatus(str, enum.Enum):
    PENDING = "pending"               # Created but payment not completed
    TRIAL = "trial"                   # Free trial period
    ACTIVE = "active"                 # Paid and currently active
    PAST_DUE = "past_due"             # Payment failed, awaiting retry
    SUSPENDED = "suspended"           # Access temporarily disabled
    CANCELLED = "cancelled"           # User cancelled subscription
    EXPIRED = "expired"               # Subscription ended and wasn't renewed

class BusinessSubscription(Base):
    __tablename__ = "business_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)

    billing_period = Column(String(50), nullable=False)  # monthly, yearly

    amount = Column(Numeric(10, 2), nullable=False)

    currency = Column(String(10), nullable=True, default="USD")

    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    auto_renew = Column(Boolean, default=True)

    is_active = Column(Boolean, default=True)
    
    #relationship
    business = relationship("Business", back_populates="subscriptions")
    service = relationship("Service")
    plan = relationship("SubscriptionPlan")
    addons = relationship("BusinessSubscriptionAddon", back_populates="subscription", cascade="all, delete-orphan")

    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    
class BusinessSubscriptionAddon(Base):
    __tablename__ = "business_subscription_addons"

    id = Column(Integer, primary_key=True)

    business_subscription_id = Column(UUID(as_uuid=True), ForeignKey("business_subscriptions.id"), nullable=False)
    addon_id = Column(Integer, ForeignKey("subscription_plan_addons.id"), nullable=False)

    quantity = Column(Integer, default=1)

    amount = Column(Numeric(10,2), nullable=False)

    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    
    #relationship
    subscription = relationship("BusinessSubscription", back_populates="addons")
    addon = relationship("SubscriptionPlanAddon")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)