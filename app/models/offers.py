from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base

class OfferType(str, enum.Enum):
    ITEM = "item"
    CATEGORY = "category"
    STORE = "store"
    BOGO = "bogo"
    COUPON = "coupon"

class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FLAT = "flat"
    FREE_ITEM = "free_item"
    MINIMUM_PURCHASE = "minimum_purchase"

class Offer(Base):
    """ 
    Offer model
    A flexible and extensible model to manage promotional offers across the system.
    Supports multiple offer types including item-level, category-level, store-wide,
    and buy-one-get-one (BOGO) offers within a single unified structure.
    
    Each offer can define either a percentage-based or flat discount, along with
    a validity period and active status. The model is designed to work with dynamic
    target mappings, allowing offers to be applied to different entities without
    requiring separate tables per offer type.
    
    BOGO-specific rules (such as buy/get quantities and optional target items)
    are handled via a dedicated metadata relation.
    """
    
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    type = Column(Enum(OfferType), nullable=False)
    discount_type = Column(Enum(DiscountType), nullable=True)
    discount_value = Column(Float, nullable=True)

    #time constraints
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    is_active = Column(Boolean, default=True)
    
    # fields for coupon type offer
    # Usage limits
    usage_limit_per_user = Column(Integer, nullable=True)
    usage_limit_total = Column(Integer, nullable=True)

    #minimum spent amount
    min_spent_amount = Column(Float, default=0.0)
    #maximum discount amount
    max_discount_amount = Column(Float, default=0.0)
    #fields for coupon type offer ends
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    # relationships
    targets = relationship("OfferTarget", back_populates="offer")
    bogo_meta = relationship("OfferBOGO", uselist=False, back_populates="offer")
    
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)


class TargetType(str, enum.Enum):
    ITEM = "item"
    CATEGORY = "category"
    STORE = "store"
    
    
class OfferTarget(Base):
    __tablename__ = "offer_targets"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"))

    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)

    offer = relationship("Offer", back_populates="targets")


class OfferBOGO(Base):
    """ 
    OfferBOGO model
    
    Stores configuration details for Buy-One-Get-One (BOGO) type offers.
    his model defines the rule-based logic for BOGO promotions linked to an Offer.
    It specifies the required quantity a customer must purchase (buy_quantity)
    and the quantity or item they will receive as a benefit (get_quantity).
    
    Optionally, it can define a specific item (get_item_id) that is rewarded,
    allowing flexibility for both same-item and cross-item BOGO promotions.

    """
    
    __tablename__ = "offer_bogo"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"))

    buy_quantity = Column(Integer, nullable=False)
    get_quantity = Column(Integer, nullable=False)

    apply_to_same_item = Column(Boolean, default=True)
    buy_item_id = Column(Integer, nullable=True)
    # optional: if different item
    get_item_id = Column(Integer, nullable=True)

    offer = relationship("Offer", back_populates="bogo_meta")