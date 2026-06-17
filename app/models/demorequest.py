from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Enum,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid

from app.core.database import Base

class DemoRequestStatus(str, enum.Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)

    # Company information
    business_name = Column(String(255), nullable=True)
    business_size = Column(String(100), nullable=True)
    business_type = Column(Text, nullable=True)
    branch_count = Column(Integer, nullable=False, default=1)
    
    # Is it existing business or new business in our system
    opening_type = Column(String(255), nullable=False)

    # Interested subscription plan
    plan_id = Column(Integer, nullable=True)

    # Demo preferences
    preferred_date = Column(DateTime, nullable=True)
    timezone = Column(String(100), nullable=True)

    # Additional requirements
    message = Column(Text, nullable=True)

    # Internal tracking
    status = Column(
        Enum(DemoRequestStatus),
        default=DemoRequestStatus.PENDING.value,
        nullable=False
    )

    assigned_to = Column(Integer, nullable=True)

    scheduled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    meeting_link = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id]
    )