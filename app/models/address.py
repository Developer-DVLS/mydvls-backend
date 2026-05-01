from app.core.database import Base

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Address(Base):
    """
    Address Model
    
    Purpose:
        Stores physical locations associated with a user.
        Linked via user_id for a One-to-Many relationship.
    """
    __tablename__ = "addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Link back to User (for Customers/Guests)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    is_default = Column(Boolean, default=False, nullable=False)
    
    # Address Details
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default="US")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # relationship 
    user = relationship("User", back_populates="addresses")
    # Link back to Location (for Businesses)
    # uselist=False makes it a 1-to-1 mapping for the location
    # location = relationship("Location", back_populates="address", uselist=False)

    def __repr__(self):
        return f"<Address(id={self.id}, city={self.city})>"
    
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join(filter(None, address_parts))