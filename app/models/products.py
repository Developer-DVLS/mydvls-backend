from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Boolean, Text, DateTime, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

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
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

class ProductAttribute(Base):
    """
    Product Attribute Model
    
    Each product can have multiple product attribute. Attributes in key and its type in value separated by comma.
    Stores technical specs like 'DPI', 'Switch Type' or 'Interface'
    """
    
    __tablename__ = "product_attributes"
    
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"))
    key = Column(String)   # e.g., "Color"
    value = Column(String) # e.g., "Matte Black"
    
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