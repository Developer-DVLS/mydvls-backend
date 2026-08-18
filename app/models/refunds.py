from decimal import Decimal
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    Column,
    Integer,
    String,
    Numeric,
    ForeignKey,
    Enum as SAEnum,
    DateTime,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RefundStatus(str, enum.Enum):
    PENDING = "pending"          # User requested refund
    PENDING_RECONCILIATION = "pending_reconciliation"   # No response from gateway
    PENDING_REVIEW = "pending_review"     # Held for review in gateway
    PROCESSING = "processing"    # Refund sent to Authorize.Net
    SUCCEEDED = "succeeded"      # Authorize.Net confirmed refund
    REJECTED = "rejected"        # Admin rejected request
    FAILED = "failed"            # Authorize.Net refund failed


class RefundType(str, enum.Enum):
    FULL = "full"
    PARTIAL = "partial"

class Refund(Base):
    __tablename__ = "refunds"
 
    id = Column(Integer, primary_key=True, index=True)
    # Order being refunded
    order_id = Column(Integer, ForeignKey(
        "orders.id", ondelete="CASCADE"), nullable=False)
    # Customer/admin requesting the refund
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Admin who approved/processed the refund
    processed_by_id =Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    refund_type = Column(String(20), default=RefundType.FULL.value,
                    nullable=False, index=True)
    status = Column(String(20), default=RefundStatus.PENDING.value,
                    nullable=False, index=True)
    
    # Requested refund amount
    amount = Column(Numeric(12, 2), nullable=False)
    # Customer/admin reason
    reason = Column(Text,nullable=True)
    
    # Amount of the order when refund was requested
    original_amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    # Amount already refunded before this refund
    previous_refunded_amount = Column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    # Authorize.Net original transaction ID
    original_transaction_id = Column(String(50),nullable=True,index=True)
    # Authorize.Net refund transaction ID
    refund_transaction_id = Column(String(50),nullable=True,unique=True,index=True)
    
    card_last4 = Column(String(4),nullable=True)
    
    gateway_response_code: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )
    gateway_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order")

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    processed_by = relationship(
        "User",
        foreign_keys=[processed_by_id],
    )
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime,nullable=True)
    completed_at = Column(DateTime,nullable=True)
    
    