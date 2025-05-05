from typing import List
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
from .schemas import(
    ComplaintCreate,
    ComplaintResponse,
    ResolveComplaintRequest,
    BulkResolveRequest,
    ResolveResponse
)
from src.auth.models import User
from src.common.db import get_db
from src.common.security import(
    get_current_user,
    is_admin
)
from src.common.enums import Status

complaint_router = APIRouter(
    prefix="/complaint",
    tags=['COMPLAINTS']
)

@complaint_router.get("/", response_model=List[ComplaintResponse])
def get_all_complaints(
    request: Request,
    current_admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    # Join Complaint and ComplaintUser tables to get all required fields
    complaint_data = db.query(
        Complaint, 
        ComplaintUser
    ).join(
        ComplaintUser, 
        Complaint.id == ComplaintUser.complaint_id
    ).all()
    
    # Format the results according to ComplaintResponse schema
    result = []
    for complaint, log in complaint_data:
        result.append(ComplaintResponse(
            complaint_id=str(complaint.id),
            created_by=str(log.created_by),
            created_at=log.created_at,
            status=complaint.status
        ))
        
    return result

@complaint_router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_by_id(
    complaint_id: UUID =  Path(...),
    current_admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    # Join Complaint and ComplaintUser tables to get all required fields
    result = db.query(
        Complaint, 
        ComplaintUser
    ).join(
        ComplaintUser, 
        Complaint.id == ComplaintUser.complaint_id
    ).filter(
        (Complaint.id) == complaint_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found."
        )
    
    complaint, log = result
    
    return ComplaintResponse(
        complaint_id=str(complaint.id),
        created_by=str(log.created_by),
        created_at=log.created_at,
        status=complaint.status
    )

@complaint_router.post("/create-complaint", response_model=ComplaintResponse)
def create_complaint(
    request: Request,
    complaint: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        new_complaint = Complaint(
            title = complaint.title,
            content = complaint.content,
            category = complaint.category,
        )
        db.add(new_complaint)
        db.flush()
        log = ComplaintUser(
                complaint_id=str(new_complaint.id),
                created_by=str(current_user.id),
            )
        db.add(log)
        db.commit()
        db.refresh(new_complaint)
        db.refresh(log)
        return ComplaintResponse(
            complaint_id=str(new_complaint.id), 
            created_by=str(log.created_by),
            created_at=log.created_at,
            status=new_complaint.status  
        )
    except Exception as e:
        db.rollback()
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
    Resolve a single complaint by ID. Only admin users can resolve complaints.
    """
    try:
        # First, check if the complaint exists
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID {complaint_id} not found."
            )
        
        # Check if the complaint is already resolved
        if complaint.status == Status.RESOLVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Complaint with ID {complaint_id} is already resolved."
            )
        
        # Update the complaint status
        complaint.status = Status.RESOLVED
        
        # Update the complaint log with resolver information
        complaint_log = db.query(ComplaintUser).filter(
            ComplaintUser.complaint_id == complaint_id
        ).first()
        
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
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
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
    """
    Resolve multiple complaints in bulk. Only admin users can resolve complaints.
    """
    if not request.complaint_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No complaint IDs provided for bulk resolution."
        )
    
    results = []
    failed_ids = []
    current_time = datetime.now()
    
    try:
        for complaint_id in request.complaint_ids:
            # Get the complaint
            complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
            
            # Skip if complaint doesn't exist or is already resolved
            if not complaint or complaint.status == Status.RESOLVED:
                failed_ids.append(str(complaint_id))
                continue
                
            # Update the complaint status
            complaint.status = Status.RESOLVED
            
            # Update the complaint log
            complaint_log = db.query(ComplaintUser).filter(
                ComplaintUser.complaint_id == complaint_id
            ).first()
            
            if complaint_log:
                complaint_log.resolved_by = current_admin.id
                complaint_log.resolved_at = current_time
                
                results.append(ResolveResponse(
                    complaint_id=str(complaint.id),
                    status=complaint.status,
                    resolved_by=str(complaint_log.resolved_by),
                    resolved_at=complaint_log.resolved_at
                ))
        
        db.commit()
        
        if failed_ids:
            # If some complaints couldn't be resolved, include a warning in the response
            for complaint_id in failed_ids:
                results.append(ResolveResponse(
                    complaint_id=str(complaint_id),
                    status=None,
                    resolved_by=None,
                    resolved_at=None,
                    message=f"Failed to resolve complaint with ID {complaint_id}. It may not exist or be already resolved."
                ))
        
        return results
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during bulk resolution: {str(e)}"
        )