from app.core.database import Base

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, func


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)

    source = Column(String)          # facebook, instagram, google, direct
    medium = Column(String)          # social, organic, email
    campaign = Column(String, nullable=True)        # summer_sale

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())