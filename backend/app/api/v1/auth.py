"""
Authentication API Endpoints
JWT-based login, logout, and token management
FIXED: Added debug logging for password verification
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from backend.app.core.database import get_db
from backend.app.models.models import User
from backend.app.core.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        logger.info(f"Verifying password...")
        logger.info(f"Hash from DB (first 20 chars): {hashed_password[:20]}")
        logger.info(f"Hash length: {len(hashed_password)}")
        
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        
        result = bcrypt.checkpw(password_bytes, hash_bytes)
        logger.info(f"Verification result: {result}")
        return result
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token
    """
    logger.info(f"Login attempt for username: {login_data.username}")
    
    # Find user
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        logger.warning(f"User not found: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"User found: {user.username}, checking password...")
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        logger.warning(f"Password verification failed for user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Password verified successfully for user: {login_data.username}")
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"User account disabled: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": str(user.user_id),
            "role": user.role.role_name if user.role else "user"
        },
        expires_delta=access_token_expires
    )
    
    logger.info(f"Login successful for user: {login_data.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": str(user.user_id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.role_name if user.role else "user",
            "is_active": user.is_active
        }
    }


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token removal)
    """
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get current user information from token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.role_name if user.role else "user",
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
