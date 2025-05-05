from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import (
    APIRouter,
    Path,
    Depends,
    status,
    HTTPException,
    Request
)
from .models import (
    Complaint,
    ComplaintUser,
)
from .schemas import(
    ComplaintCreate,
    ComplaintResponse,
)
from src.auth.models import User
from src.common.db import get_db
from src.common.security import(
    get_current_user,
    is_admin
)

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
            created_at=log.created_at,  # Include created_at from the log
            status=new_complaint.status  
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the complaint."
        )