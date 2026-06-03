import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    Enum
)
from sqlalchemy.sql import func

from app.core.database import Base


class TaxScope(str, enum.Enum):
    PRODUCT = "product"
    SUBSCRIPTION = "subscription"
    SERVICE = "service"
    SHIPPING = "shipping"
    GLOBAL = "global"
    

class TaxConfig(Base):
    __tablename__ = "taxes"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    # eg VAT, GST, SERVICE
    code = Column(String(50), unique=True, nullable=False)
    
    tax_scope = Column(Enum(TaxScope), nullable=False, default=TaxScope.PRODUCT)

    tax_percentage = Column( Numeric(5, 2), nullable=False)

    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return self.name