"""
Export API Endpoints
REFACTORED: Supplier → Entity
Export validated data in various formats (Oracle Fusion CSV, comparison reports)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
from backend.app.services.oracle_exporter import OracleFusionExporter
import uuid
import os

router = APIRouter()

@router.get("/jobs/{job_id}/export/oracle-fusion")
async def export_oracle_fusion(
    job_id: str,
    include_metadata: bool = False,
    db: Session = Depends(get_db)
):
    """
    Export job to Oracle Fusion CSV format
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(Entity.job_id == job_uuid).all()
    if not entities:
        raise HTTPException(status_code=400, detail="No entities found in job")
    
    # Export
    exporter = OracleFusionExporter()
    filepath = exporter.export_job_to_csv(job, entities, include_metadata)
    
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=os.path.basename(filepath),
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(filepath)}"}
    )

@router.get("/jobs/{job_id}/export/high-confidence")
async def export_high_confidence_only(
    job_id: str,
    min_confidence: float = 90.0,
    db: Session = Depends(get_db)
):
    """
    Export only HIGH confidence records (Oracle Fusion ready)
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(Entity.job_id == job_uuid).all()
    
    try:
        exporter = OracleFusionExporter()
        filepath = exporter.export_high_confidence_only(job, entities, min_confidence)
        
        return FileResponse(
            filepath,
            media_type="text/csv",
            filename=os.path.basename(filepath),
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(filepath)}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{job_id}/export/for-review")
async def export_for_review(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Export records that need manual review with full metadata
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(Entity.job_id == job_uuid).all()
    
    try:
        exporter = OracleFusionExporter()
        filepath = exporter.export_for_review(job, entities)
        
        return FileResponse(
            filepath,
            media_type="text/csv",
            filename=os.path.basename(filepath),
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(filepath)}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{job_id}/export/comparison")
async def export_comparison_report(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Export before/after comparison report
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(Entity.job_id == job_uuid).all()
    if not entities:
        raise HTTPException(status_code=400, detail="No entities found in job")
    
    exporter = OracleFusionExporter()
    filepath = exporter.export_comparison_report(job, entities)
    
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=os.path.basename(filepath),
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(filepath)}"}
    )

@router.get("/jobs/{job_id}/export/summary")
async def get_export_summary(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for export
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(Entity.job_id == job_uuid).all()
    if not entities:
        raise HTTPException(status_code=400, detail="No entities found in job")
    
    exporter = OracleFusionExporter()
    summary = exporter.generate_summary_report(job, entities)
    
    return summary
