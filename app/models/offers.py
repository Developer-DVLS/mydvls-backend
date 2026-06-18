from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, Numeric, String, Enum, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin

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

class Offer(SoftDeleteMixin, Base):
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
    
    
class OfferTarget(SoftDeleteMixin, Base):
    __tablename__ = "offer_targets"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"))

    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)

    offer = relationship("Offer", back_populates="targets")


class OfferBOGO(SoftDeleteMixin, Base):
    """ 
    OfferBOGO model
    
    Stores configuration details for Buy-One-Get-One (BOGO) type offers.
    This model defines the rule-based logic for BOGO promotions linked to an Offer.
    It specifies the required quantity a customer must purchase (buy_quantity)
    and the quantity or item they will receive as a benefit (get_quantity).
    
    BOGO offer is attached to product-variant; buy_item_id and get_item_id refers to product-variant-id.
    
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


## combo offer

class ComboDiscountType(str, enum.Enum):
    COMBO_PRICE = "combo_price"
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    
class ComboOffer(SoftDeleteMixin, Base):
    """ 
    Combo offer model

    ComboOffer represents a predefined product bundle where a 
    fixed set of product variants are grouped together and sold
    under a special pricing rule.

    It supports two discount strategies:
    - a fixed combo price for the entire bundle, or
    - a percentage discount applied to the total price of included items.
    
    Each combo has a validity period, priority for conflict resolution, 
    and a stackable flag that controls whether it can be combined with other promotions.
    """
    
    __tablename__ = "combo_offers"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

    start_date = Column(DateTime)
    end_date = Column(DateTime)

    discount_type = Column(Enum(ComboDiscountType), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=True)
    
    priority = Column(Integer, default=0)
    stackable = Column(Boolean, default=True)

    items = relationship(
        "ComboOfferItem",
        back_populates="offer",
        cascade="all, delete-orphan"
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class ComboOfferItem(SoftDeleteMixin, Base):
    """ 
    ComboOfferItem defines the individual product variants that belong to a ComboOffer.
    
    Each item specifies:
    - the product variant included in the combo
    - the required quantity of that variant within the bundle
    
    This model enables precise control over bundle composition, 
    ensuring that only specific variants (not just products) are eligible for the combo offer.
    """
    
    __tablename__ = "combo_offer_items"

    id = Column(Integer, primary_key=True)

    combo_offer_id = Column(
        Integer,
        ForeignKey("combo_offers.id", ondelete="CASCADE")
    )

    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True
    )
    product_id = Column(
        Integer, 
        ForeignKey("products.id"), 
        nullable=True
    )

    quantity = Column(Integer, default=1)

    offer = relationship("ComboOffer", back_populates="items")
    product_variant = relationship("ProductVariant")
    product = relationship("Product")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)