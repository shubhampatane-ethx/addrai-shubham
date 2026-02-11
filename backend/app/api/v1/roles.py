from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.role import Role

router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get("/dropdown")
def role_dropdown(db: Session = Depends(get_db)):
    roles = db.query(Role).order_by(Role.role_name).all()
    return [
        {
            "value": role.role_id,
            "label": role.role_name
        }
        for role in roles
    ]
