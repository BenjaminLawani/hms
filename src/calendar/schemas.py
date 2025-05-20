# In your schemas file (e.g., schemas/event.py or schemas.py)
from pydantic import BaseModel, validator,UUID4
from datetime import datetime
from typing import Optional

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values, **kwargs):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel): # For partial updates
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None

    @validator('end_time', always=True) # always=True to run even if start_time is not provided in update
    def end_time_must_be_after_start_time_update(cls, v, values, **kwargs):
        start_time = values.get('start_time')
        # If only end_time is provided, we can't validate against start_time directly from payload.
        # This validation is better handled if we fetch the existing event in the CRUD and compare.
        # For now, if start_time is in the payload, validate.
        if start_time and v and v <= start_time:
            raise ValueError('End time must be after start time')
        return v


class EventRead(EventBase):
    id: UUID4
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # created_by_id: Optional[int] = None # If you add it to model

    class Config:
        orm_mode = True