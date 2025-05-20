from sqlalchemy.orm import Session
from .models import Event 
from .schemas import EventCreate, EventUpdate
from typing import List, Optional

def create_event(db: Session, event: EventCreate) -> Event:
    db_event = Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_event(db: Session, event_id: int) -> Optional[Event]:
    return db.query(Event).filter(Event.id == event_id).first()

def get_events(db: Session, skip: int = 0, limit: int = 100) -> List[Event]:
    return db.query(Event).order_by(Event.start_time.asc()).offset(skip).limit(limit).all()

def update_event(db: Session, event_id: int, event_update: EventUpdate) -> Optional[Event]:
    db_event = get_event(db, event_id)
    if db_event:
        update_data = event_update.dict(exclude_unset=True)
        
        # Handle potential start_time/end_time validation for updates
        current_start_time = db_event.start_time
        current_end_time = db_event.end_time

        new_start_time = update_data.get('start_time', current_start_time)
        new_end_time = update_data.get('end_time', current_end_time)

        if new_start_time and new_end_time and new_end_time <= new_start_time:
            raise ValueError("End time must be after start time")

        for key, value in update_data.items():
            setattr(db_event, key, value)
        
        db.commit()
        db.refresh(db_event)
    return db_event

def delete_event(db: Session, event_id: int) -> Optional[Event]:
    db_event = get_event(db, event_id)
    if db_event:
        db.delete(db_event)
        db.commit()
    return db_event # Returns the deleted object or None