from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .schemas import (
    EventCreate,
    EventRead,
    EventUpdate
)
from src.common.db import get_db
from src.common.security import get_current_user, is_admin
router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"],
)
from .services import (
    get_event,
    get_events,
    create_event,
    update_event,
    delete_event
)
@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_new_event_route(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(is_admin) # Admin only
):
    try:
        return create_event(db=db, event=event)
    except ValueError as e: # Catch validation errors from Pydantic or CRUD
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[EventRead])
def read_events_route(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Students and Admins
):
    events = get_events(db, skip=skip, limit=limit)
    return events

@router.get("/{event_id}", response_model=EventRead)
def read_single_event_route(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(is_admin) # Students and Admins
):
    db_event = get_event(db, event_id=event_id)
    if db_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return db_event

@router.put("/{event_id}", response_model=EventRead)
def update_existing_event_route(
    event_id: UUID,
    event_update: EventUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(is_admin) # Admin only
):
    try:
        db_event = update_event(db=db, event_id=event_id, event_update=event_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    if db_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for update")
    return db_event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_event_route(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(is_admin) # Admin only
):
    deleted_event = delete_event(db=db, event_id=event_id)
    if deleted_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for deletion")
    return # FastAPI handles 204 with no body