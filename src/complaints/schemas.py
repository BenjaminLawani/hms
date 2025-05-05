from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

from src.common.enums import Status, ComplainCategory

class ComplaintCreate(BaseModel):
    title: str
    content: Optional[str]
    category: Optional[ComplainCategory]

class ComplaintResponse(BaseModel):
    complaint_id: str
    created_by: str
    created_at: datetime
    status: Optional[Status]