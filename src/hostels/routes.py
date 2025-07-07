from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from uuid import UUID
from .models import Hall, Room
from .schemas import (
    HallOccupancyStats,
    BulkAllocationCreate,
    BulkRoomCreate,
    RoomAllocationCreate,
    RoomAllocationResponse,
    HallCreate,
    HallUpdate,
    HallResponse,
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    HallAllocationSummary
)
from .service import RoomAllocationService
from src.common.enums import AllocationStatus
from src.common.db import get_db
from src.common.security import is_admin

hall_router = APIRouter(
    prefix="/halls",
    tags=["HALLS"]
)
room_router = APIRouter(
    prefix="/rooms",
    tags=["ROOMS"]
)
allocation_router = APIRouter(
    prefix="/allocate",
    tags=["ROOM ALLOCATION"]
)

# Hall CRUD routes
@hall_router.get("/", response_model=List[HallResponse])
def get_all_halls(db: Session = Depends(get_db)):
    """Get all halls"""
    service = RoomAllocationService(db)
    return service.get_all_halls()

@hall_router.post("/", response_model=HallResponse, status_code=status.HTTP_201_CREATED)
def create_hall(
    hall: HallCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Create a new hall"""
    
    service = RoomAllocationService(db)
    try:
        return service.create_hall(
            name=hall.name,
            no_of_rooms=hall.no_of_rooms,
            min_level=hall.min_level,
            max_level=hall.max_level,
            is_open_for_allocation=hall.is_open_for_allocation,
            academic_year=hall.academic_year
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@hall_router.get("/{hall_id}", response_model=HallResponse)
def get_hall_by_id(
    hall_id: str,
    db: Session = Depends(get_db)
):
    """Get hall details by ID"""
    service = RoomAllocationService(db)
    try:
        return service.get_hall(hall_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@hall_router.put("/{hall_id}", response_model=HallResponse)
def update_hall_details(
    hall_id: str,
    hall: HallUpdate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Update hall details"""
    
    service = RoomAllocationService(db)
    try:
        update_data = hall.dict(exclude_unset=True)
        return service.update_hall(hall_id=hall_id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@hall_router.delete("/{hall_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hall(
    hall_id: str,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Delete a hall"""
    
    service = RoomAllocationService(db)
    try:
        service.delete_hall(hall_id)
        return {"message": "Hall deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@hall_router.get("/{hall_id}/rooms", response_model=List[RoomResponse])
def get_rooms_by_hall(
    hall_id: str,
    db: Session = Depends(get_db)
):
    """Get all rooms in a hall"""
    service = RoomAllocationService(db)
    try:
        return service.get_rooms_by_hall(hall_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Room CRUD routes
@room_router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room: RoomCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Create a new room in a hall"""
    
    service = RoomAllocationService(db)
    try:
        return service.create_room(
            hall_id=str(room.hall_id),
            room_number=room.room_number,
            capacity=room.capacity
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@room_router.get("/{room_id}", response_model=RoomResponse)
def get_room_by_id(
    room_id: int,
    db: Session = Depends(get_db)
):
    """Get room details by ID"""
    service = RoomAllocationService(db)
    try:
        return service.get_room(room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@room_router.put("/{room_id}", response_model=RoomResponse)
def update_room_details(
    room_id: int,
    room: RoomUpdate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Update room details"""
    
    service = RoomAllocationService(db)
    try:
        update_data = room.dict(exclude_unset=True)
        return service.update_room(room_id=room_id, **update_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@room_router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Delete a room"""
    
    service = RoomAllocationService(db)
    try:
        service.delete_room(room_id)
        return {"message": "Room deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Room allocation routes (updating/fixing the existing ones)
@allocation_router.post("/", response_model=RoomAllocationResponse, status_code=status.HTTP_201_CREATED)
def create_allocation(
    allocation: RoomAllocationCreate,
    db: Session = Depends(get_db)
):
    """Allocate a user to a room"""
    service = RoomAllocationService(db)
    try:
        result = service.allocate_room(
            user_id=(allocation.user_id),
            room_id=allocation.room_id,
            academic_year=allocation.academic_year
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.post("/bulk", response_model=List[RoomAllocationResponse], status_code=status.HTTP_201_CREATED)
def bulk_allocate(
    bulk_allocation: BulkAllocationCreate,
    db: Session = Depends(get_db)
):
    """Bulk allocate users to rooms in a hall"""
    service = RoomAllocationService(db)
    try:
        # Convert UUID4 objects to strings
        user_ids = [str(id) for id in bulk_allocation.user_ids]
        hall_id = str(bulk_allocation.hall_id)
        
        allocations = service.bulk_allocate_rooms(
            user_ids=user_ids,
            hall_id=hall_id,
            academic_year=bulk_allocation.academic_year
        )
        return allocations
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.put("/{allocation_id}/vacate", response_model=RoomAllocationResponse)
def vacate_room(
    allocation_id: str,
    db: Session = Depends(get_db)
):
    """Mark a room as vacated"""
    service = RoomAllocationService(db)
    try:
        result = service.vacate_room(allocation_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.get("/user/{user_id}", response_model=RoomAllocationResponse)
def get_user_allocation(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a user's current allocation"""
    service = RoomAllocationService(db)
    allocation = service.get_user_allocation(user_id)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active allocation found for this user"
        )
    return allocation

@allocation_router.get("/halls/{hall_id}/stats", response_model=HallOccupancyStats)
def get_hall_occupancy_stats(
    hall_id: str,
    db: Session = Depends(get_db)
):
    """Get occupancy statistics for a hall"""
    service = RoomAllocationService(db)
    try:
        stats = service.get_hall_occupancy_stats(hall_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.get("/available-rooms/{hall_id}", response_model=List[RoomResponse])
def get_available_rooms(
    hall_id: str,
    db: Session = Depends(get_db)
):
    """Get rooms in a hall that have space available"""
    service = RoomAllocationService(db)
    try:
        rooms = service.get_available_rooms(hall_id)
        return rooms
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.get("/allocations", response_model=List[RoomAllocationResponse])
def get_all_allocations(
    status: Optional[AllocationStatus] = None,
    hall_id: Optional[str] = None,
    academic_year: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Get all room allocations with optional filters"""
    
    service = RoomAllocationService(db)
    try:
        filters = {}
        if status:
            filters["status"] = status
        if hall_id:
            filters["hall_id"] = hall_id
        if academic_year:
            filters["academic_year"] = academic_year
            
        allocations = service.get_all_allocations(**filters)
        return allocations
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@allocation_router.get("/{allocation_id}", response_model=RoomAllocationResponse)
def get_allocation_by_id(
    allocation_id: str,
    db: Session = Depends(get_db)
):
    """Get allocation details by ID"""
    service = RoomAllocationService(db)
    try:
        allocation = service.get_allocation_by_id(allocation_id)
        return allocation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@hall_router.put("/{hall_id}/allocation-status", response_model=HallResponse)
def set_hall_allocation_status(
    hall_id: str,
    is_open: bool,
    academic_year: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Open or close a hall for allocation"""
    
    service = RoomAllocationService(db)
    try:
        hall = service.set_hall_allocation_status(hall_id, is_open, academic_year)
        return hall
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@hall_router.get("/{hall_id}/summary", response_model=HallAllocationSummary)
def get_hall_allocation_summary(
    hall_id: str,
    db: Session = Depends(get_db)
):
    """Get allocation summary statistics for a hall"""
    service = RoomAllocationService(db)
    try:
        summary = service.get_hall_allocation_summary(hall_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
@room_router.post("/bulk", response_model=List[RoomResponse], status_code=status.HTTP_201_CREATED)
def create_rooms_bulk(
    bulk_rooms: BulkRoomCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(is_admin)
):
    """Create multiple rooms in a hall at once"""
    
    service = RoomAllocationService(db)
    try:
        # Extract hall_id as string
        hall_id = str(bulk_rooms.hall_id)
        
        # Convert rooms to dictionaries while ensuring all rooms have the same hall_id
        rooms_data = []
        for room in bulk_rooms.rooms:
            # Ensure the hall_id in each room matches the main hall_id
            if str(room.hall_id) != hall_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All rooms must have the same hall_id as the parent request"
                )
            
            rooms_data.append({
                "room_number": room.room_number,
                "capacity": room.capacity
            })
        
        return service.create_rooms_bulk(hall_id=hall_id, rooms_data=rooms_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
