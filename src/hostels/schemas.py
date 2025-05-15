from datetime import datetime
from typing import List, Optional
from pydantic import (
    BaseModel,
    UUID4,
    validator,
    Field
)
from src.common.enums import AllocationStatus

class RoomAllocationCreate(BaseModel):
    user_id: UUID4
    room_id: int
    academic_year: str
    
    @validator('academic_year')
    def validate_academic_year(cls, v):
        # Validate academic year format (e.g., "2024-2025")
        if not v or not '-' in v:
            raise ValueError('Academic year must be in format YYYY-YYYY')
        return v
    
class BulkAllocationCreate(BaseModel):
    user_ids: List[UUID4]
    hall_id: UUID4
    academic_year: str
    
    @validator('academic_year')
    def validate_academic_year(cls, v):
        if not v or not '-' in v:
            raise ValueError('Academic year must be in format YYYY-YYYY')
        return v

class RoomAllocationResponse(BaseModel):
    id: UUID4
    user_id: Optional[UUID4] | None
    room_id: int
    hall_id: UUID4
    status: AllocationStatus
    allocated_at: datetime
    vacated_at: Optional[datetime] = None
    academic_year: str
    created_at: datetime
    
    class Config:
        orm_mode = True
        
class HallOccupancyStats(BaseModel):
    hall_name: str
    total_capacity: int
    current_occupancy: int
    occupancy_rate: float
    available_spaces: int
    
class HallAllocationSummary(BaseModel):
    hall_name: str
    academic_year: Optional[str]
    is_open_for_allocation: bool
    total_rooms: int
    full_rooms: int
    available_rooms: int
    total_capacity: int
    current_occupancy: int
    available_spaces: int
    active_allocations: int
    pending_allocations: int
    vacated_allocations: int

# Hall schemas
class HallCreate(BaseModel):
    name: str
    no_of_rooms: int
    min_level: int
    max_level: int
    is_open_for_allocation: bool = False
    academic_year: Optional[str] = None
    
    @validator('academic_year')
    def validate_academic_year(cls, v):
        if v and not '-' in v:
            raise ValueError('Academic year must be in format YYYY-YYYY')
        return v

class HallUpdate(BaseModel):
    name: Optional[str] = None
    no_of_rooms: Optional[int] = None
    min_level: Optional[int] = None
    max_level: Optional[int] = None
    is_open_for_allocation: Optional[bool] = None
    academic_year: Optional[str] = None
    
    @validator('academic_year')
    def validate_academic_year(cls, v):
        if v and not '-' in v:
            raise ValueError('Academic year must be in format YYYY-YYYY')
        return v

class HallResponse(BaseModel):
    id: UUID4
    name: str
    no_of_rooms: int
    min_level: int
    max_level: int
    total_available_capacity: Optional[int]
    is_open_for_allocation: bool
    academic_year: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True

# Room schemas
class RoomCreate(BaseModel):
    hall_id: UUID4
    room_number: str
    capacity: int

class RoomUpdate(BaseModel):
    room_number: Optional[str] = None
    capacity: Optional[int] = None
    is_available: Optional[bool] = None

class RoomResponse(BaseModel):
    id: int
    hall_id: UUID4
    room_number: str
    capacity: int
    current_occupancy: int
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True

class BulkRoomCreate(BaseModel):
    hall_id: UUID4
    rooms: List[RoomCreate]

    @validator('rooms')
    def validate_rooms(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one room must be provided')
        
        # Check for duplicate room numbers within the submission
        room_numbers = [room.room_number for room in v]
        if len(room_numbers) != len(set(room_numbers)):
            raise ValueError('Duplicate room numbers are not allowed')
            
        return v