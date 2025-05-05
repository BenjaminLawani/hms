from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Union
from uuid import UUID

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

class ResolveComplaintRequest(BaseModel):
    """Schema for resolving a single complaint request."""
    pass  # No extra data needed for resolving a single complaint

class BulkResolveRequest(BaseModel):
    """Schema for bulk resolving complaints request."""
    complaint_ids: List[UUID]

class ResolveResponse(BaseModel):
    """Schema for complaint resolution response."""
    complaint_id: str
    status: Optional[Status]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    message: Optional[str] = None