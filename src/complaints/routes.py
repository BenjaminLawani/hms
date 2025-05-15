from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import (
    APIRouter,
    Path,
    Depends,
    status,
    HTTPException,
    Request,
    Body
)
from datetime import datetime
from .models import (
    Complaint,
    ComplaintUser,
)
# Assuming ComplainCategory is defined in src.common.enums
from src.common.enums import Status, ComplainCategory
from .schemas import(
    ComplaintCreate,
    # ComplaintResponse, # Will define a more complete one below for clarity
    ResolveComplaintRequest,
    BulkResolveRequest,
    ResolveResponse
)
from src.auth.models import User # Import User model
from src.common.db import get_db
from src.common.security import(
    get_current_user,
    is_admin
)
# from src.common.enums import Status # Already imported

complaint_router = APIRouter(
    prefix="/complaint",
    tags=['COMPLAINTS']
)

# Define a Pydantic model for ComplaintResponse that matches admin dashboard needs
# This should ideally be in your schemas.py and imported.
from pydantic import BaseModel

class FullComplaintResponse(BaseModel):
    complaint_id: str
    title: Optional[str] = None
    details: Optional[str] = None # Mapped from Complaint.content
    category: Optional[ComplainCategory] = None
    created_by: str # User ID of the creator
    created_by_name: Optional[str] = None # Name of the creator
    user_level: Optional[str] = None # Level of the creator
    created_at: datetime
    status: Status
    resolved_by: Optional[str] = None # User ID of the resolver
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True # Pydantic V2, or orm_mode = True for V1
        use_enum_values = True # Ensures enum values (e.g., "PENDING") are used


@complaint_router.get("/", response_model=List[FullComplaintResponse])
def get_all_complaints(
    request: Request,
    current_admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    # Join Complaint, ComplaintUser, and User (for creator details)
    complaint_data = db.query(
        Complaint,
        ComplaintUser,
        User  # User model for the creator
    ).join(
        ComplaintUser, Complaint.id == ComplaintUser.complaint_id
    ).join(
        User, ComplaintUser.created_by == User.id  # Join on creator's ID
    ).all()

    result = []
    for complaint, complaint_log, creator_user in complaint_data:
        result.append(FullComplaintResponse(
            complaint_id=str(complaint.id),
            title=complaint.title,
            details=complaint.content, # Use content for details
            category=complaint.category,
            created_by=str(complaint_log.created_by),
            created_by_name=creator_user.name, # Get creator's name
            user_level=str(creator_user.level) if creator_user.level else None, # Get creator's level
            created_at=complaint_log.created_at,
            status=complaint.status, # This is the crucial field
            resolved_by=str(complaint_log.resolved_by) if complaint_log.resolved_by else None,
            resolved_at=complaint_log.resolved_at
        ))
        
    return result

@complaint_router.get("/{complaint_id}", response_model=FullComplaintResponse)
def get_complaint_by_id(
    complaint_id: UUID =  Path(...),
    current_admin: User = Depends(is_admin), 
    db: Session = Depends(get_db)
):
    # Join Complaint, ComplaintUser, and User (for creator details)
    data = db.query(
        Complaint,
        ComplaintUser,
        User # User model for the creator
    ).join(
        ComplaintUser, Complaint.id == ComplaintUser.complaint_id
    ).join(
        User, ComplaintUser.created_by == User.id # Join on creator's ID
    ).filter(
        Complaint.id == complaint_id
    ).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found."
        )
    
    complaint, complaint_log, creator_user = data
    
    return FullComplaintResponse(
        complaint_id=str(complaint.id),
        title=complaint.title,
        details=complaint.content,
        category=complaint.category,
        created_by=str(complaint_log.created_by),
        created_by_name=creator_user.name,
        user_level=str(creator_user.level) if creator_user.level else None,
        created_at=complaint_log.created_at,
        status=complaint.status,
        resolved_by=str(complaint_log.resolved_by) if complaint_log.resolved_by else None,
        resolved_at=complaint_log.resolved_at
    )

@complaint_router.post("/create-complaint", response_model=FullComplaintResponse)
def create_complaint(
    request: Request,
    complaint: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # This is the creator
):
    try:
        new_complaint = Complaint(
            title = complaint.title,
            content = complaint.content,
            category = complaint.category,            )
        db.add(new_complaint)
        db.flush() 
        log = ComplaintUser(
                complaint_id=new_complaint.id, 
                created_by=current_user.id,
            )
        db.add(log)
        db.commit()
        db.refresh(new_complaint)
        db.refresh(log)

        return FullComplaintResponse(
            complaint_id=str(new_complaint.id), 
            title=new_complaint.title,
            details=new_complaint.content,
            category=new_complaint.category,
            created_by=str(log.created_by), # Should be current_user.id
            created_by_name=current_user.name, # Creator's name
            user_level=str(current_user.level) if current_user.level else None, # Creator's level
            created_at=log.created_at,
            status=new_complaint.status, # Should be PENDING
            resolved_by=None, # New complaints are not resolved
            resolved_at=None  # New complaints are not resolved
        )
    except Exception as e:
        db.rollback()
        # It's good practice to log the actual error e
        print(f"Error in create_complaint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the complaint."
        )

@complaint_router.put("/{complaint_id}/resolve", response_model=ResolveResponse)
def resolve_complaint(
    complaint_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin)
):
    """
    Resolve a single complaint by ID.
    """
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {complaint_id} not found."
            )
        
        if complaint.status == Status.RESOLVED:
            # Return current resolved state instead of raising an error, or choose to error.
            # For idempotency, often good to return current state.
            complaint_log_existing = db.query(ComplaintUser).filter(ComplaintUser.complaint_id == complaint_id).first()
            return ResolveResponse(
                complaint_id=str(complaint.id),
                status=complaint.status,
                resolved_by=str(complaint_log_existing.resolved_by) if complaint_log_existing and complaint_log_existing.resolved_by else None,
                resolved_at=complaint_log_existing.resolved_at if complaint_log_existing else None,
                message="Complaint was already resolved."
            )
        
        complaint.status = Status.RESOLVED
        
        complaint_log = db.query(ComplaintUser).filter(
            ComplaintUser.complaint_id == complaint_id
        ).first()
        
        if not complaint_log: # Should not happen if complaint exists
            raise HTTPException(status_code=500, detail="Complaint log missing for existing complaint.")

        complaint_log.resolved_by = current_admin.id
        complaint_log.resolved_at = datetime.now()
        
        db.commit()
        db.refresh(complaint)
        db.refresh(complaint_log)
        
        return ResolveResponse(
            complaint_id=str(complaint.id),
            status=complaint.status,
            resolved_by=str(complaint_log.resolved_by),
            resolved_at=complaint_log.resolved_at
        )
    except HTTPException as e:
        db.rollback() # Rollback only if it's an HTTP exception we raised, otherwise commit might have happened.
                      # Better to put commit at the very end of try block if all ops succeed.
        raise e
    except Exception as e:
        db.rollback()
        print(f"Error in resolve_complaint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while resolving the complaint: {str(e)}"
        )

@complaint_router.post("/bulk-resolve", response_model=List[ResolveResponse])
def bulk_resolve_complaints(
    request: BulkResolveRequest = Body(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin)
):
    if not request.complaint_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No complaint IDs provided for bulk resolution."
        )
    
    results = []
    current_time = datetime.now() # Use a single timestamp for all resolved in this batch
    
    # Fetch all relevant complaints and logs in fewer queries if possible
    complaints_to_update = db.query(Complaint).filter(
        Complaint.id.in_(request.complaint_ids),
        Complaint.status != Status.RESOLVED # Only act on non-resolved ones
    ).all()

    complaint_ids_found = {c.id for c in complaints_to_update}

    for complaint_id_req in request.complaint_ids:
        if complaint_id_req not in complaint_ids_found:
            results.append(ResolveResponse(
                complaint_id=str(complaint_id_req),
                status=None, # Or fetch current status to report it
                resolved_by=None,
                resolved_at=None,
                message=f"Complaint with ID {complaint_id_req} not found or already resolved."
            ))

    if not complaints_to_update: # All were not found or already resolved
        db.commit() # Commit any other pending changes if any, or just return
        return results

    try:
        for complaint in complaints_to_update:
            complaint.status = Status.RESOLVED
            
            complaint_log = db.query(ComplaintUser).filter(
                ComplaintUser.complaint_id == complaint.id
            ).first()
            
            if complaint_log: # Should always exist
                complaint_log.resolved_by = current_admin.id
                complaint_log.resolved_at = current_time
                
                results.append(ResolveResponse(
                    complaint_id=str(complaint.id),
                    status=complaint.status,
                    resolved_by=str(complaint_log.resolved_by),
                    resolved_at=complaint_log.resolved_at
                ))
            else: # Should not happen
                 results.append(ResolveResponse(
                    complaint_id=str(complaint.id),
                    status=complaint.status, # Status is updated in memory
                    resolved_by=None,
                    resolved_at=None,
                    message=f"Complaint log not found for {complaint.id}, but status updated in transaction."
                ))
        
        db.commit() # Commit all changes at once
        
        return results
    except Exception as e:
        db.rollback()
        print(f"Error in bulk_resolve_complaints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during bulk resolution: {str(e)}"
        )