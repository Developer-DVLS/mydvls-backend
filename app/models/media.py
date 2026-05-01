from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Media(Base):
    """ 
    Image media library model for across the platform.
    """
    
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    
    file_name = Column(String)
    file_path = Column(String)  # The URL or S3 path
    file_type = Column(String)  # e.g., 'image/jpeg'
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)