from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from .models import Hall, Room, RoomAllocation
from .schemas import HallOccupancyStats, RoomAllocationResponse
from src.common.enums import AllocationStatus


class RoomAllocationService:
    def __init__(self, db: Session):
        self.db = db

    def allocate_room(self, user_id: str, room_id: int, academic_year: str) -> RoomAllocationResponse:
        """Allocate a user to a room"""
        # Check if user already has an active allocation
        existing_allocation = self.db.query(RoomAllocation).filter(
            RoomAllocation.user_id == user_id,
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).first()
        
        if existing_allocation:
            raise ValueError(f"User already has an active room allocation")
        
        # Get the room to check availability
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"Room with ID {room_id} not found")
            
        if room.current_occupancy >= room.capacity:
            raise ValueError(f"Room {room.room_number} is already at full capacity")
            
        if not room.is_available:
            raise ValueError(f"Room {room.room_number} is not available for allocation")
        
        # Get the hall
        hall = self.db.query(Hall).filter(Hall.id == room.hall_id).first()
        if not hall.is_open_for_allocation:
            raise ValueError(f"Hall {hall.name} is not open for allocation")
            
        # Create the allocation
        allocation = RoomAllocation(
            user_id=user_id,
            room_id=room_id,
            hall_id=hall.id,
            status=AllocationStatus.ALLOCATED,
            academic_year=academic_year
        )
        
        # Update room occupancy
        room.current_occupancy += 1
        if room.current_occupancy >= room.capacity:
            room.is_available = False
            
        # Update hall available capacity
        if hall.total_available_capacity is not None:
            hall.total_available_capacity -= 1
        
        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(allocation)
        
        return allocation

    def bulk_allocate_rooms(self, user_ids: List[str], hall_id: str, academic_year: str) -> List[RoomAllocationResponse]:
        """Bulk allocate users to rooms in a hall"""
        # Check hall exists and is open for allocation
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
            
        if not hall.is_open_for_allocation:
            raise ValueError(f"Hall {hall.name} is not open for allocation")
        
        # Get available rooms in the hall
        available_rooms = self.db.query(Room).filter(
            Room.hall_id == hall_id,
            Room.is_available == True,
            Room.current_occupancy < Room.capacity
        ).all()
        
        if not available_rooms:
            raise ValueError(f"No available rooms in hall {hall.name}")
            
        # Calculate total available spaces
        total_available_spaces = sum(room.capacity - room.current_occupancy for room in available_rooms)
        
        if len(user_ids) > total_available_spaces:
            raise ValueError(f"Not enough space for all users. Available: {total_available_spaces}, Requested: {len(user_ids)}")
        
        # Check if any users already have active allocations
        existing_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.user_id.in_(user_ids),
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).all()
        
        if existing_allocations:
            user_ids_with_allocations = [str(alloc.user_id) for alloc in existing_allocations]
            raise ValueError(f"Some users already have active allocations: {', '.join(user_ids_with_allocations)}")
        
        allocations = []
        room_index = 0
        
        for user_id in user_ids:
            current_room = available_rooms[room_index]
            
            # Create allocation
            allocation = RoomAllocation(
                user_id=user_id,
                room_id=current_room.id,
                hall_id=hall_id,
                status=AllocationStatus.ALLOCATED,
                academic_year=academic_year
            )
            
            # Update room occupancy
            current_room.current_occupancy += 1
            if current_room.current_occupancy >= current_room.capacity:
                current_room.is_available = False
                room_index += 1
            
            # Update hall available capacity
            if hall.total_available_capacity is not None:
                hall.total_available_capacity -= 1
                
            allocations.append(allocation)
            self.db.add(allocation)
        
        self.db.commit()
        
        # Refresh all allocations
        for allocation in allocations:
            self.db.refresh(allocation)
            
        return allocations

    def vacate_room(self, allocation_id: str) -> RoomAllocationResponse:
        """Mark a room allocation as vacated"""
        allocation = self.db.query(RoomAllocation).filter(RoomAllocation.id == allocation_id).first()
        if not allocation:
            raise ValueError(f"Allocation with ID {allocation_id} not found")
            
        if allocation.status != AllocationStatus.ALLOCATED:
            raise ValueError(f"Allocation is not active (current status: {allocation.status})")
        
        # Update allocation
        allocation.status = AllocationStatus.VACATED
        allocation.vacated_at = datetime.now()
        
        # Update room occupancy
        room = self.db.query(Room).filter(Room.id == allocation.room_id).first()
        room.current_occupancy -= 1
        room.is_available = True
        
        # Update hall available capacity
        hall = self.db.query(Hall).filter(Hall.id == allocation.hall_id).first()
        if hall.total_available_capacity is not None:
            hall.total_available_capacity += 1
        
        self.db.commit()
        self.db.refresh(allocation)
        
        return allocation

    def get_user_allocation(self, user_id: str) -> Optional[RoomAllocationResponse]:
        """Get a user's current active allocation"""
        allocation = self.db.query(RoomAllocation).filter(
            RoomAllocation.user_id == user_id,
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).first()
        
        return allocation

    def get_hall_occupancy_stats(self, hall_id: str) -> HallOccupancyStats:
        """Get occupancy statistics for a hall"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        # Count total capacity and current occupancy
        total_capacity = self.db.query(func.sum(Room.capacity)).filter(Room.hall_id == hall_id).scalar() or 0
        current_occupancy = self.db.query(func.sum(Room.current_occupancy)).filter(Room.hall_id == hall_id).scalar() or 0
        
        # Calculate stats
        occupancy_rate = (current_occupancy / total_capacity) * 100 if total_capacity > 0 else 0
        available_spaces = total_capacity - current_occupancy
        
        return HallOccupancyStats(
            hall_name=hall.name,
            total_capacity=total_capacity,
            current_occupancy=current_occupancy,
            occupancy_rate=occupancy_rate,
            available_spaces=available_spaces
        )

    def get_available_rooms(self, hall_id: str) -> List[Room]:
        """Get rooms in a hall that have space available"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        available_rooms = self.db.query(Room).filter(
            Room.hall_id == hall_id,
            Room.is_available == True,
            Room.current_occupancy < Room.capacity
        ).all()
        
        return available_rooms
        
    def get_all_allocations(self, **filters) -> List[RoomAllocation]:
        """Get all room allocations with optional filters"""
        query = self.db.query(RoomAllocation)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(RoomAllocation, key):
                    query = query.filter(getattr(RoomAllocation, key) == value)
        
        return query.all()
        
    def set_hall_allocation_status(self, hall_id: str, is_open: bool, academic_year: Optional[str] = None) -> Hall:
        """Open or close a hall for allocation"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        hall.is_open_for_allocation = is_open
        if academic_year:
            hall.academic_year = academic_year
            
        self.db.commit()
        self.db.refresh(hall)
        return hall
        
    def get_allocation_by_id(self, allocation_id: str) -> RoomAllocation:
        """Get allocation by ID"""
        allocation = self.db.query(RoomAllocation).filter(RoomAllocation.id == allocation_id).first()
        if not allocation:
            raise ValueError(f"Allocation with ID {allocation_id} not found")
        return allocation
        
    def get_hall_allocation_summary(self, hall_id: str) -> dict:
        """Get allocation summary for a hall"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
            
        # Get rooms
        rooms = self.db.query(Room).filter(Room.hall_id == hall_id).all()
        
        # Count allocations by status
        active_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.hall_id == hall_id,
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).count()
        
        pending_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.hall_id == hall_id,
            RoomAllocation.status == AllocationStatus.PENDING
        ).count()
        
        vacated_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.hall_id == hall_id,
            RoomAllocation.status == AllocationStatus.VACATED
        ).count()
        
        # Calculate additional stats
        total_capacity = sum(room.capacity for room in rooms)
        current_occupancy = sum(room.current_occupancy for room in rooms)
        available_spaces = total_capacity - current_occupancy
        full_rooms = sum(1 for room in rooms if room.current_occupancy >= room.capacity)
        available_rooms = sum(1 for room in rooms if room.current_occupancy < room.capacity and room.is_available)
        
        return {
            "hall_name": hall.name,
            "academic_year": hall.academic_year,
            "is_open_for_allocation": hall.is_open_for_allocation,
            "total_rooms": len(rooms),
            "full_rooms": full_rooms,
            "available_rooms": available_rooms,
            "total_capacity": total_capacity,
            "current_occupancy": current_occupancy,
            "available_spaces": available_spaces,
            "active_allocations": active_allocations,
            "pending_allocations": pending_allocations,
            "vacated_allocations": vacated_allocations
        }

    # Hall CRUD methods
    def create_hall(self, name: str, no_of_rooms: int, min_level: int, max_level: int, 
                    is_open_for_allocation: bool = False, academic_year: str = None) -> Hall:
        """Create a new hall"""
        hall = Hall(
            name=name,
            no_of_rooms=no_of_rooms,
            min_level=min_level,
            max_level=max_level,
            is_open_for_allocation=is_open_for_allocation,
            academic_year=academic_year,
            total_available_capacity=0  # Will be updated after rooms are created
        )
        
        self.db.add(hall)
        self.db.commit()
        self.db.refresh(hall)
        
        return hall
    
    def get_hall(self, hall_id: str) -> Hall:
        """Get a hall by ID"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        return hall
    
    def get_all_halls(self) -> List[Hall]:
        """Get all halls"""
        return self.db.query(Hall).all()
    
    def update_hall(self, hall_id: str, **kwargs) -> Hall:
        """Update hall details"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(hall, key):
                setattr(hall, key, value)
        
        self.db.commit()
        self.db.refresh(hall)
        return hall
    
    def delete_hall(self, hall_id: str) -> bool:
        """Delete a hall"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        # Check if there are active allocations
        active_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.hall_id == hall_id,
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).first()
        
        if active_allocations:
            raise ValueError(f"Cannot delete hall with active allocations")
        
        self.db.delete(hall)
        self.db.commit()
        return True
    
    # Room CRUD methods
    def create_room(self, hall_id: str, room_number: str, capacity: int) -> Room:
        """Create a new room in a hall"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        # Check if room number already exists in this hall
        existing_room = self.db.query(Room).filter(
            Room.hall_id == hall_id,
            Room.room_number == room_number
        ).first()
        
        if existing_room:
            raise ValueError(f"Room {room_number} already exists in this hall")
        
        room = Room(
            hall_id=hall_id,
            room_number=room_number,
            capacity=capacity,
            current_occupancy=0,
            is_available=True
        )
        
        self.db.add(room)
        
        # Update hall total available capacity
        if hall.total_available_capacity is not None:
            hall.total_available_capacity += capacity
        else:
            hall.total_available_capacity = capacity
        
        self.db.commit()
        self.db.refresh(room)
        
        return room
    
    def get_room(self, room_id: int) -> Room:
        """Get a room by ID"""
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"Room with ID {room_id} not found")
        return room
    
    def get_rooms_by_hall(self, hall_id: str) -> List[Room]:
        """Get all rooms in a hall"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
            
        return self.db.query(Room).filter(Room.hall_id == hall_id).all()
    
    def update_room(self, room_id: int, **kwargs) -> Room:
        """Update room details"""
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"Room with ID {room_id} not found")
        
        old_capacity = room.capacity
        
        for key, value in kwargs.items():
            if hasattr(room, key):
                setattr(room, key, value)
        
        # If capacity changed, update hall total available capacity
        if 'capacity' in kwargs and kwargs['capacity'] != old_capacity:
            hall = self.db.query(Hall).filter(Hall.id == room.hall_id).first()
            capacity_diff = kwargs['capacity'] - old_capacity
            if hall.total_available_capacity is not None:
                hall.total_available_capacity += capacity_diff
        
        self.db.commit()
        self.db.refresh(room)
        return room
    
    def delete_room(self, room_id: int) -> bool:
        """Delete a room"""
        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"Room with ID {room_id} not found")
        
        # Check if there are active allocations for this room
        active_allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.room_id == room_id,
            RoomAllocation.status == AllocationStatus.ALLOCATED
        ).first()
        
        if active_allocations:
            raise ValueError(f"Cannot delete room with active allocations")
        
        # Update hall total available capacity
        hall = self.db.query(Hall).filter(Hall.id == room.hall_id).first()
        if hall.total_available_capacity is not None:
            hall.total_available_capacity -= (room.capacity - room.current_occupancy)
        
        self.db.delete(room)
        self.db.commit()
        return True
    
    def create_rooms_bulk(self, hall_id: str, rooms_data: List[dict]) -> List[Room]:
        """Create multiple rooms in a hall at once"""
        hall = self.db.query(Hall).filter(Hall.id == hall_id).first()
        if not hall:
            raise ValueError(f"Hall with ID {hall_id} not found")
        
        # Check if any room numbers already exist in this hall
        room_numbers = [room['room_number'] for room in rooms_data]
        existing_rooms = self.db.query(Room).filter(
            Room.hall_id == hall_id,
            Room.room_number.in_(room_numbers)
        ).all()
        
        if existing_rooms:
            existing_numbers = [room.room_number for room in existing_rooms]
            raise ValueError(f"The following room numbers already exist in this hall: {', '.join(existing_numbers)}")
        
        created_rooms = []
        total_capacity_increase = 0
        
        for room_data in rooms_data:
            room = Room(
                hall_id=hall_id,
                room_number=room_data['room_number'],
                capacity=room_data['capacity'],
                current_occupancy=0,
                is_available=True
            )
            
            self.db.add(room)
            created_rooms.append(room)
            total_capacity_increase += room_data['capacity']
        
        # Update hall total available capacity
        if hall.total_available_capacity is not None:
            hall.total_available_capacity += total_capacity_increase
        else:
            hall.total_available_capacity = total_capacity_increase
        
        self.db.commit()
        
        # Refresh all rooms
        for room in created_rooms:
            self.db.refresh(room)
        
        return created_rooms