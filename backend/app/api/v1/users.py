"""
User Management API Endpoints
CRUD operations for users (admin only)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
import bcrypt
from backend.app.core.database import get_db
from backend.app.models.models import AssignedValidator, User, Role, ValidatorConfig
from backend.app.core.dependencies import require_admin, get_current_user

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None
    role_name: str = "user"  # admin or user
    assigned_validator: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role_name: Optional[str] = None
    assigned_validator: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    assigned_validator: Optional[str]
    is_active: bool
    last_login: Optional[str]
    created_at: str


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    """
    users = db.query(User)\
        .order_by(User.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return [
        {
            "user_id": str(user.user_id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.role_name if user.role else "user",
            "assigned_validator": user.assigned_validator,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only)
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Get role
    role = db.query(Role).filter(Role.role_name == user_data.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{user_data.role_name}' not found")
    
    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role_id=role.role_id,
        assigned_validator=user_data.assigned_validator,
        created_by=current_user.user_id,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign validator if provided
    if user_data.assigned_validator:
        validator = db.query(ValidatorConfig).filter(
        ValidatorConfig.validator_type == user_data.assigned_validator
    ).first()

    if not validator:
        raise HTTPException(status_code=400, detail="Validator not found")

        assignment = AssignedValidator(
        user_id=new_user.user_id,
        validator_config_id=validator.config_id
    )

    db.add(assignment)
    db.commit()
    
    return {
        "user_id": str(new_user.user_id),
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.role_name if new_user.role else "user",
        "assigned_validator": new_user.assigned_validator,
        "is_active": new_user.is_active,
        "last_login": None,
        "created_at": new_user.created_at.isoformat() if new_user.created_at else None
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get user details (admin only)
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.role_name if user.role else "user",
        "assigned_validator": user.assigned_validator,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user (admin only)
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from disabling themselves
    if str(user.user_id) == str(current_user.user_id) and user_data.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    # Update fields
    if user_data.email is not None:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.user_id != user_uuid
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = user_data.email
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.role_name is not None:
        role = db.query(Role).filter(Role.role_name == user_data.role_name).first()
        if not role:
            raise HTTPException(status_code=400, detail=f"Role '{user_data.role_name}' not found")
        user.role_id = role.role_id
    
    if user_data.assigned_validator is not None:
    # Remove existing assignments
        db.query(AssignedValidator).filter(
        AssignedValidator.user_id == user.user_id
    ).delete()

    # Find validator config
        validator = db.query(ValidatorConfig).filter(
        ValidatorConfig.validator_type == user_data.assigned_validator
    ).first()

    if not validator:
        raise HTTPException(status_code=400, detail="Validator not found")

    # Create new assignment
        assignment = AssignedValidator(
        user_id=user.user_id,
        validator_config_id=validator.config_id
    )

    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.add(assignment)
    db.commit()
    db.refresh(user)
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.role_name if user.role else "user",
        "assigned_validator": user.assigned_validator,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete user (admin only)
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if str(user.user_id) == str(current_user.user_id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully", "user_id": user_id}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    new_password: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reset user password (admin only)
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}
