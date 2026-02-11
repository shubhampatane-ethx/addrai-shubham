"""
Jobs API Endpoints
Create, list, validate, and manage validation jobs
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity, User
from backend.app.core.config import settings
from backend.app.tasks.validation import validate_entities_task
from backend.app.core.dependencies import get_current_user
from backend.app.models.models import AssignedValidator, ValidatorConfig
import pandas as pd
import uuid
from datetime import datetime
import os

router = APIRouter()


# =========================
# Pydantic Models
# =========================

class JobUpdateRequest(BaseModel):
    job_name: Optional[str] = None
    client_name: Optional[str] = None


class JobValidateRequest(BaseModel):
    prompt: Optional[str] = ""


# =========================
# Upload Job
# =========================

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    job_name: str = "Untitled Job",
    client_name: str = "",
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel and CSV files are allowed")

    job = ValidationJob(
        job_name=job_name,
        client_name=client_name,
        uploaded_file_name=file.filename,
        status='UPLOADED'
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    file_path = os.path.join(settings.UPLOAD_DIR, f"{job.job_id}_{file.filename}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    job.uploaded_file_path = file_path

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df = df.fillna('').replace(
            ['nan', 'NaN', 'NAN', 'None', 'none', 'NONE'], '',
            regex=False
        )
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        entities = []
        for idx, row in df.iterrows():
            entities.append(Entity(
                job_id=job.job_id,
                row_number=idx + 2,
                entity_name_original=row.get('entity_name_original', ''),
                address1_original=row.get('address1_original', ''),
                address2_original=row.get('address2_original', ''),
                address3_original=row.get('address3_original', ''),
                city_original=row.get('city_original', ''),
                state_original=row.get('state_original', ''),
                zip_original=row.get('zip_original', ''),
                country_original=row.get('country_original', 'US')
            ))

        db.bulk_save_objects(entities)
        job.total_records = len(entities)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")

    return {
        "job_id": str(job.job_id),
        "job_name": job.job_name,
        "total_records": job.total_records,
        "status": job.status,
        "message": "File uploaded successfully. Ready for validation."
    }


# =========================
# List Jobs
# =========================

@router.get("")
async def list_jobs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    jobs = (
        db.query(ValidationJob)
        .order_by(ValidationJob.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "jobs": [
            {
                "job_id": str(job.job_id),
                "job_name": job.job_name,
                "client_name": job.client_name,
                "status": job.status,
                "total_records": job.total_records,
                "processed_records": job.processed_records,
                "progress_percentage": float(job.progress_percentage or 0),
                "high_confidence": job.high_confidence,
                "medium_confidence": job.medium_confidence,
                "low_confidence": job.low_confidence,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ],
        "total": db.query(ValidationJob).count()
    }


# =========================
# Start Validation
# =========================

@router.post("/{job_id}/validate")
async def start_validation(
    job_id: str,
    request: JobValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ['UPLOADED', 'FAILED']:
        raise HTTPException(
            status_code=400,
            detail=f"Job status is '{job.status}'. Cannot start validation."
        )

    # Fetch assigned validator from DB
    assignment = db.query(AssignedValidator).filter(
        AssignedValidator.user_id == current_user.user_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=403,
            detail="No validator assigned to this user"
        )

    validator_config = db.query(ValidatorConfig).filter(
        ValidatorConfig.config_id == assignment.validator_config_id,
        ValidatorConfig.enabled == True
    ).first()

    if not validator_config:
        raise HTTPException(
            status_code=403,
            detail="Assigned validator is disabled"
        )

    selected_validator = validator_config.validator_type


    task = validate_entities_task.delay(
        str(job_uuid),
        selected_validator,
        request.prompt or ""
    )

    job.status = 'QUEUED'
    job.current_step = 'Validation queued'
    db.commit()

    return {
        "message": "Validation started",
        "job_id": str(job.job_id),
        "task_id": task.id,
        "validator_type": selected_validator,
        "status": "queued"
    }


# =========================
# Delete Job
# =========================

@router.delete("/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.uploaded_file_path and os.path.exists(job.uploaded_file_path):
        os.remove(job.uploaded_file_path)

    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully", "job_id": job_id}
