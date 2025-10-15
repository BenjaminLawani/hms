from sqlalchemy.orm import Session
from typing import List, Optional
from src.common.enums import AllocationStatus
from datetime import datetime
import logging

from src.hostels.models import RoomAllocation, Room, Hall

class AccountDeletionHandler:
    """Handler for cleaning up room allocations when deleting a user account"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def handle_user_deletion(self, user_id: str) -> dict:
        """
        Handle cleanup of room allocations when a user is deleted
        
        This function:
        1. Finds all active allocations for the user
        2. Vacates rooms by updating room and hall capacities
        3. Updates allocation status to VACATED instead of nullifying user_id
        4. Returns a summary of the actions taken
        
        Args:
            user_id: The ID of the user being deleted
            
        Returns:
            dict: Summary of allocations handled
        """
        # Find all allocations for this user
        allocations = self.db.query(RoomAllocation).filter(
            RoomAllocation.user_id == user_id
        ).all()
        
        if not allocations:
            return {"message": "No allocations found for this user", "allocations_handled": 0}
        
        active_count = 0
        other_count = 0
        
        for allocation in allocations:
            if allocation.status == AllocationStatus.ALLOCATED:
                active_count += 1
                
                # Update room occupancy
                room = self.db.query(Room).filter(Room.id == allocation.room_id).first()
                if room:
                    room.current_occupancy -= 1
                    room.is_available = True
                
                # Update hall available capacity
                hall = self.db.query(Hall).filter(Hall.id == allocation.hall_id).first()
                if hall and hall.total_available_capacity is not None:
                    hall.total_available_capacity += 1
                
                # Mark allocation as vacated instead of nullifying user_id
                allocation.status = AllocationStatus.VACATED
                allocation.vacated_at = datetime.now()
            else:
                other_count += 1
        
        # Commit the changes
        self.db.commit()
        
        return {
            "message": f"Successfully handled room allocations for deleted user",
            "active_allocations_vacated": active_count,
            "other_allocations_found": other_count
        }
