from pydantic import BaseModel, HttpUrl, computed_field
from typing import Optional

from app.core.config import settings

class MediaResponse(BaseModel):
    id: int
    file_path: str  # Stored as "/static/uploads/uuid.jpg"
    
    @computed_field
    @property
    def full_url(self) -> str:
        # You can pull the base domain from an Environment Variable
        base_url = settings.BASE_URL
        return f"{base_url}{self.file_path}"

    class Config:
        from_attributes = True