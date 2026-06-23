import enum
from sqlalchemy import Column, Enum, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base

class CareerStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    OFFER_SENT = "offer_sent"
    HIRED = "hired"
    REJECTED = "rejected"

class Career(Base):
    __tablename__ = "careers"

    id = Column(Integer, primary_key=True, index=True)

    # Applicant details
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(Text, nullable=False)

    # Job details
    position = Column(String(255), nullable=True)

    # Additional information
    cover_letter = Column(Text, nullable=True)

    # Resume file path / URL
    resume = Column(String(500), nullable=False)

    # Optional links
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # Dynamic questions & answers
    qna = Column(JSON, nullable=True)
    
    notes = Column(Text, nullable=True)
    status = Column(Enum(CareerStatus), nullable=False, default=CareerStatus.NEW.value)

    created_at = Column(DateTime(timezone=True), server_default=func.now())