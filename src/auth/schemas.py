from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    level: Optional[int]
    department: Optional[str]
    email: EmailStr
    password: str
    profile_photo_url: Optional[str] | None
    created_at: datetime
    phone_number: Optional[str] | None

class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    level: Optional[int]
    department: Optional[str]
    phone_number: Optional[str] | None
    profile_photo_url: Optional[str] | None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    profile_photo_url: Optional[str]

class UserForgotPassword(BaseModel):
    email: EmailStr