from typing import List, Annotated
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Request,
    Path,
    Response
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from .models import User
from .schemas import (
    UserCreate,
    UserResponse,
    UserForgotPassword,
    UserUpdate,
    Token
)
templates = Jinja2Templates(directory="templates")
from src.common.db import get_db
from src.common.security import (
    create_access_token,
    hash_password,
    verify_password,
    is_admin,
    get_current_user,
    generate_random_password,
    send_password_reset_email
)
from src.common.config import ACCESS_TOKEN_EXPIRES
from src.common.handlers import AccountDeletionHandler  # Import the handler

limiter = Limiter(key_func=get_remote_address)
auth_router = APIRouter(
    prefix="/auth",
    tags=["AUTH"]
)
profile_router = APIRouter(
    prefix="/profile",
    tags=["PROFILE"]
)

user_router = APIRouter(
    prefix="/users",
    tags=["USERS"]
)

@auth_router.post("/login", response_model=Token)
# @limiter.limit("3/hour")
def login_user(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.email == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid Credentials"
        )
    access_token = create_access_token(
        data={
            "sub": str(db_user.id),
            "email": db_user.email,
            "is_admin": db_user.is_admin
        },
        expires_delta=timedelta(seconds=ACCESS_TOKEN_EXPIRES)
    )
    # Set redirect URL in a header or cookie
    redirect_url = "/dashboard/admin-dashboard" if db_user.is_admin else "/dashboard/student-dashboard"
    response.headers["X-Redirect-URL"] = redirect_url
    
    # Return the token data
    return {"access_token": access_token, "token_type": "bearer"}
    

@auth_router.post("/get-started", response_model=UserResponse)
def get_started(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_mail = db.query(User).filter(User.email == user.email).first()
    if existing_mail:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail= "Email already registered"
        )
    new_user = User(
        email = user.email,
        name = f"{user.first_name} {user.last_name}",
        level = user.level,
        hashed_password = hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id = str(new_user.id),
        name = new_user.name,
        email = new_user.email,
        level = new_user.level,
        profile_photo_url= new_user.avatar_url
    )

@profile_router.put("/update-profile", response_model=UserResponse)
def update_user_profile(
    request: Request,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Update user details
    if user_update.first_name or user_update.last_name:
        # If either first name or last name is provided, update the name
        first_name = user_update.first_name if user_update.first_name else current_user.name.split()[0]
        last_name = user_update.last_name if user_update.last_name else (
            current_user.name.split()[1] if len(current_user.name.split()) > 1 else ""
        )
        current_user.name = f"{first_name} {last_name}"
    
    # Update profile photo if provided
    if user_update.profile_photo_url:
        current_user.avatar_url = user_update.profile_photo_url
    
    # Save changes to database
    db.commit()
    db.refresh(current_user)
    
    # Return updated user information
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        level=current_user.level,
        profile_photo_url=current_user.avatar_url
    )

@profile_router.delete("/delete-account")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    # First, handle room allocations
    try:
        # handler = AccountDeletionHandler(db)
        # allocation_result = handler.handle_user_deletion(str(current_user.id))
        
        # Then proceed with account deletion
        db.delete(current_user)
        db.commit()
        
        return {
            "message": "Account deleted successfully"
            # "allocations_handled": allocation_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Account deletion failed: {str(e)}"
        )
    
@auth_router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: Request,
    user_data: UserForgotPassword,
    db: Session = Depends(get_db)
):
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        # For security reasons, don't reveal if the email exists or not
        # Just return success message regardless
        return {"message": "If your email is registered, you will receive an email with your new password"}
    
    try:
        # Generate a random password
        new_password = generate_random_password(12)
        
        # Update user's password in the database
        user.hashed_password = hash_password(new_password)
        db.commit()
        
        # Send email with new password - directly, not in background
        await send_password_reset_email(
            email_to=user.email,
            user_name=user.name,
            new_password=new_password
        )
        
        return {"message": "If your email is registered, you will receive an email with your new password"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )

@user_router.get("/", response_model=List[UserResponse])
def get_all_users(
    request: Request,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    result = []
    for user in users:
        result.append(UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            level=user.level,
            profile_photo_url=user.avatar_url,
        ))
    return result  

@user_router.delete("/{user_id}", response_model=dict)
def delete_user_by_id(
    request: Request,
    user_id: UUID = Path(...), 
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter((User.id) == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # First, handle room allocations
        handler = AccountDeletionHandler(db)
        allocation_result = handler.handle_user_deletion(str(user_id))
        
        # Then proceed with account deletion
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User with id: {user_id} deleted successfully",
            "allocations_handled": allocation_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"User deletion failed: {str(e)}"
        )

@user_router.put("/{user_id}", response_model=UserResponse)
def admin_update_user_details(
    request: Request,
    user_id: UUID,
    user_update: UserUpdate,
    admin: User = Depends(is_admin),
    db: Session = Depends(get_db)
):
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user details
    if user_update.first_name or user_update.last_name:
        # If either first name or last name is provided, update the name
        first_name = user_update.first_name if user_update.first_name else user.name.split()[0]
        last_name = user_update.last_name if user_update.last_name else (
            user.name.split()[1] if len(user.name.split()) > 1 else ""
        )
        user.name = f"{first_name} {last_name}"
    
    # Update profile photo if provided
    if user_update.profile_photo_url:
        user.avatar_url = user_update.profile_photo_url
    
    # Save changes to database
    db.commit()
    db.refresh(user)
    
    # Return updated user information
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        level=user.level,
        profile_photo_url=user.avatar_url
    )

@auth_router.get("/login")
def root(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@auth_router.get("/get-started")
def root(request: Request):
    return templates.TemplateResponse('signup.html', {'request': request})

@profile_router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        level=current_user.level,
        profile_photo_url=current_user.avatar_url
    )