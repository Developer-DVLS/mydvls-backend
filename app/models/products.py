from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Boolean, Text, DateTime, Table, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base

class ProductCategory(Base):
    """ 
    Product Category Model
    """
    
    __tablename__ = "product_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    
    ordering = Column(Integer, default=0, index=True)
    
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class Product(Base):
    """ 
    Product Model
    """
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    
    category = relationship("ProductCategory", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    variant_options = relationship("VariantOption", back_populates="product",cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class VariantOption(Base):
    __tablename__ = "product_options"
    
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "name",
            name="uq_product_option"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True
    )

    name = Column(String, nullable=False)  # Color, Size, Till Size
    is_active = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    
    product = relationship("Product", back_populates="variant_options")

    values = relationship(
        "VariantOptionValue",
        back_populates="variant_option",
        cascade="all, delete-orphan"
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    
    
product_variant_options_value = Table(
    "product_variant_options_value",
    Base.metadata,
    Column("product_variant_id", Integer, ForeignKey("product_variants.id"), primary_key=True),
    Column("variant_option_value_id", Integer, ForeignKey("variant_option_values.id"), primary_key=True),
)

class VariantOptionValue(Base):
    __tablename__ = "variant_option_values"
    
    __table_args__ = (
        UniqueConstraint(
            "option_id",
            "value",
            name="uq_option_value"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    option_id = Column(
        Integer,
        ForeignKey("product_options.id", ondelete="CASCADE"),
        index=True
    )

    value = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    description = Column(Text, nullable=True)

    variant_option = relationship("VariantOption", back_populates="values")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class ProductVariant(Base):
    """ 
    Product Variation Model
    """
    
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku = Column(String, unique=True, index=True)
    price = Column(Numeric(10, 2), default=0.00, nullable=False)
    cost_price = Column(Numeric(10, 2), default=0.00, nullable=False)
    margin = Column(Numeric(10, 2), default=0.00, nullable=False)
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)
    
    # relationship
    product = relationship("Product", back_populates="variants")
    attributes = relationship("ProductAttribute", back_populates="variant", cascade="all, delete-orphan")
    images = relationship("ProductVariantImage", back_populates="variant", cascade="all, delete-orphan")
    
    variant_options = relationship(
        "VariantOptionValue",
        secondary=product_variant_options_value
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    
    @property
    def product_name(self):
        return self.product.name if self.product else None
    
    @hybrid_property
    def in_stock(self):
        return self.is_active and self.stock_quantity > 0

class ProductAttribute(Base):
    """
    Product Attribute Model
    
    Each product can have multiple product attribute. Attributes in key and its type in value separated by comma.
    Stores technical specs like 'DPI', 'Switch Type' or 'Interface'
    """
    
    __tablename__ = "product_attributes"
    
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"))
    key = Column(String) 
    value = Column(String)
    
    # relationship
    variant = relationship("ProductVariant", back_populates="attributes")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class ProductVariantImage(Base):
    """ 
    Product Variation Image Model
    
    Each product variation can have multiple images.
    """
    
    __tablename__ = "product_variant_images"
    
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"))
    image_url = Column(String)
    
    # relationship
    variant = relationship("ProductVariant", back_populates="images")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)