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
        if not current_user: # Safeguard, though get_current_user should raise 401
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated."
            )
            
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
    # if not current_admin: # Safeguard for current_admin being None
    #     # This case should ideally be caught by the is_admin dependency
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin user not properly authenticated or authorized."
    #     )
        
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {complaint_id} not found."
            )
        
        if complaint.status == Status.RESOLVED:
            complaint_log_existing = db.query(ComplaintUser).filter(ComplaintUser.complaint_id == complaint_id).first()
            return ResolveResponse(
                complaint_id=str(complaint.id), # Ensure complaint_id is string
                status=complaint.status,
                resolved_by=str(complaint_log_existing.resolved_by) if complaint_log_existing and complaint_log_existing.resolved_by else None,
                resolved_at=complaint_log_existing.resolved_at if complaint_log_existing else None,
                message="Complaint was already resolved."
            )
        
        complaint.status = Status.RESOLVED
        
        complaint_log = db.query(ComplaintUser).filter(
            ComplaintUser.complaint_id == complaint_id
        ).first()
        
        if not complaint_log: 
            # This situation implies data inconsistency, as a complaint should always have a log.
            # Rollback status change on complaint if log is missing for atomicity.
            db.rollback() # Rollback the complaint.status change
            raise HTTPException(status_code=500, detail="Complaint log missing for existing complaint. Resolution aborted.")

        complaint_log.resolved_by = current_admin.id # This line caused the error if current_admin was None
        complaint_log.resolved_at = datetime.now()
        
        db.commit()
        db.refresh(complaint)
        db.refresh(complaint_log)
        
        return ResolveResponse(
            complaint_id=str(complaint.id), # Ensure complaint_id is string
            status=complaint.status,
            resolved_by=str(complaint_log.resolved_by) if complaint_log.resolved_by else None, # Ensure resolved_by is string
            resolved_at=complaint_log.resolved_at
        )
    except HTTPException: # Re-raise HTTPExceptions directly
        db.rollback() 
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in resolve_complaint: {e}") # Log the original error
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
    # if not current_admin: # Safeguard for current_admin being None
    #     # This case should ideally be caught by the is_admin dependency
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin user not properly authenticated or authorized."
    #     )

    if not request.complaint_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No complaint IDs provided for bulk resolution."
        )
    
    results = []
    current_time = datetime.now() 
    
    complaint_uuids = []
    for complaint_id_str_or_uuid in request.complaint_ids:
        try:
            # Handle both string UUIDs and UUID objects if the frontend sends mixed types
            if isinstance(complaint_id_str_or_uuid, UUID):
                complaint_uuids.append(complaint_id_str_or_uuid)
            else:
                complaint_uuids.append(UUID(str(complaint_id_str_or_uuid)))
        except ValueError:
            results.append(ResolveResponse(
                complaint_id=str(complaint_id_str_or_uuid),
                status=None, # Explicitly set None for status as per schema
                resolved_by=None,
                resolved_at=None,
                message=f"Invalid UUID format: {str(complaint_id_str_or_uuid)}"
            ))
    
    # Filter out complaint_ids that already have a result due to invalid format
    valid_complaint_uuids_to_process = [
        uid for uid in complaint_uuids 
        if str(uid) not in (r.complaint_id for r in results if r.message and "Invalid UUID format" in r.message)
    ]

    if not valid_complaint_uuids_to_process:
        return results # Return results if all were invalid UUIDs or list was empty

    # Fetch complaints that are not yet resolved
    complaints_to_update = db.query(Complaint).filter(
        Complaint.id.in_(valid_complaint_uuids_to_process),
        Complaint.status != Status.RESOLVED
    ).all()
    
    complaint_ids_to_update = {c.id for c in complaints_to_update}

    # Fetch corresponding complaint logs for those to be updated
    complaint_logs_dict = {
        log.complaint_id: log 
        for log in db.query(ComplaintUser).filter(ComplaintUser.complaint_id.in_(complaint_ids_to_update)).all()
    }
    
    # Handle complaints that were not found or already resolved among the valid UUIDs
    for uid in valid_complaint_uuids_to_process:
        if uid not in complaint_ids_to_update: # Not in the list of "to be updated"
            # Check if it exists at all or is already resolved
            existing_complaint = db.query(Complaint).filter(Complaint.id == uid).first()
            if existing_complaint:
                if existing_complaint.status == Status.RESOLVED:
                    # Fetch its log to provide resolved_by/at details
                    existing_log = db.query(ComplaintUser).filter(ComplaintUser.complaint_id == uid).first()
                    results.append(ResolveResponse(
                        complaint_id=str(uid),
                        status=existing_complaint.status,
                        resolved_by=str(existing_log.resolved_by) if existing_log and existing_log.resolved_by else None,
                        resolved_at=existing_log.resolved_at if existing_log else None,
                        message="Complaint was already resolved."
                    ))
                # else: complaint exists but status is not PENDING nor RESOLVED (if other statuses exist)
                # This case is unlikely if only PENDING/RESOLVED are used for this flow.
            else: # Complaint not found
                results.append(ResolveResponse(
                    complaint_id=str(uid),
                    status=None, # Explicitly set None for status
                    resolved_by=None,
                    resolved_at=None,
                    message=f"Complaint with ID {str(uid)} not found."
                ))

    if not complaints_to_update: # All valid UUIDs were either not found or already resolved
        return results

    try:
        for complaint in complaints_to_update:
            complaint.status = Status.RESOLVED
            
            complaint_log = complaint_logs_dict.get(complaint.id)
            
            if complaint_log:
                complaint_log.resolved_by = current_admin.id # This line caused the error
                complaint_log.resolved_at = current_time
                
                results.append(ResolveResponse(
                    complaint_id=str(complaint.id),
                    status=complaint.status,
                    resolved_by=str(complaint_log.resolved_by) if complaint_log.resolved_by else None,
                    resolved_at=complaint_log.resolved_at
                ))
            else: 
                # Data inconsistency: complaint exists but its log doesn't.
                # The status of this complaint is updated in memory, but we might choose to not commit it
                # or handle it differently. For now, report it.
                results.append(ResolveResponse(
                    complaint_id=str(complaint.id),
                    status=complaint.status, # Status is updated in memory
                    resolved_by=None,
                    resolved_at=None,
                    message=f"Complaint log not found for {complaint.id}. Status updated in transaction, but log details incomplete."
                ))
        
        db.commit()
        
        return results  
    except Exception as e:
        db.rollback()
        print(f"Error in bulk_resolve_complaints: {e}") # Log the original error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during bulk resolution: {str(e)}"
        )