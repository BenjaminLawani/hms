from uuid import UUID
import string, random
from fastapi.security import OAuth2PasswordBearer
from fastapi import (
    HTTPException,
    Depends,
    status
)
from fastapi_mail import (
    MessageSchema,
    FastMail
)
from sqlalchemy.orm import Session
from src.auth.models import User
from datetime import (
    datetime,
    UTC,
    timedelta
)
from passlib.context import CryptContext
from jwt import encode, decode

from .config import JWT_KEY, EMAIL_CONFIG
from .db import get_db

pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def jwt_encode(data):
    return encode(data, JWT_KEY, "HS256")

def jwt_decode(token):
    return decode(token, JWT_KEY, ["HS256"])

def create_access_token(data: dict, expires_delta: timedelta=None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt_encode(to_encode)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt_decode(token)
        user_id: UUID = payload.get("sub")
        is_admin: bool = payload.get("is_admin")
        if is_admin is None:
            raise credentials_exception
        
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def is_admin(current_user: User = Depends(get_current_user)):
    if current_user.is_admin == False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Not an administrator"
        )
    

def generate_random_password(length=12):
    """
    Generate a random password with specified length
    """
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one of each type for strong password
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # Shuffle the password
    random.shuffle(password)
    
    return ''.join(password)

async def send_password_reset_email(email_to: str, user_name: str, new_password: str):
    """
    Send an email with the new generated password
    """
    # Create HTML and plain text content
    html_content = f"""
    <html>
      <body>
        <h2>Password Reset</h2>
        <p>Hi {user_name},</p>
        <p>We received a request to reset your password. Your new password is:</p>
        <p><strong>{new_password}</strong></p>
        <p>Please log in with this password and then change it immediately for security reasons.</p>
        <p>If you didn't request this password reset, please contact our support team immediately.</p>
      </body>
    </html>
    """
    
    message = MessageSchema(
        subject="Your New Password",
        recipients=[email_to],
        body=html_content,
        subtype="html"
    )
    
    # Create FastMail instance
    fm = FastMail(EMAIL_CONFIG)
    
    # Send email
    await fm.send_message(message)
    
    return {"message": "Email has been sent"}