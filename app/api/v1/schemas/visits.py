from typing import Optional
from pydantic import BaseModel

class VisitCreate(BaseModel):
    source: str
    medium: str
    campaign: Optional[str] = None