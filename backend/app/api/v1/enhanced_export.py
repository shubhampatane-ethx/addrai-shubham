"""
Enhanced Export Endpoint
REFACTORED: Supplier → Entity
Export with Original, Validated (OSM), and Oracle columns
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
import csv
import io
from datetime import datetime

router = APIRouter()


@router.get("/job/{job_id}/complete")
async def export_complete_csv(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Export complete CSV with Original, Validated, and Oracle columns
    """
    try:
        # Get job
        job = db.query(ValidationJob).filter(
            ValidationJob.job_id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get all entities
        entities = db.query(Entity).filter(
            Entity.job_id == job_id
        ).order_by(Entity.row_number).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row with all column sets
        headers = [
            # Original columns
            'Original_Entity_Name',
            'Original_Address1',
            'Original_Address2',
            'Original_City',
            'Original_State',
            'Original_ZIP',
            'Original_Country',
            
            # Validated (OSM) columns
            'OSM_Entity_Name',
            'OSM_Address1',
            'OSM_Address2',
            'OSM_City',
            'OSM_State',
            'OSM_ZIP',
            'OSM_Country',
            'OSM_Latitude',
            'OSM_Longitude',
            
            # Oracle-formatted columns
            'Oracle_Entity_Name',
            'Oracle_Address1',
            'Oracle_Address2',
            'Oracle_City',
            'Oracle_State',
            'Oracle_ZIP',
            'Oracle_Country',
            
            # Validation metadata
            'Confidence_Score',
            'Confidence_Level',
            'Record_Status',
            'Validation_Source',
            'Has_Geocoding',
            'Validated_Date',
            
            # USPS formatted
            'USPS_Delivery_Line_1',
            'USPS_Delivery_Line_2',
            'USPS_Last_Line'
        ]
        
        writer.writerow(headers)
        
        # Data rows
        for entity in entities:
            row = [
                # Original
                entity.entity_name_original or '',
                entity.address1_original or '',
                entity.address2_original or '',
                entity.city_original or '',
                entity.state_original or '',
                entity.zip_original or '',
                entity.country_original or '',
                
                # OSM Validated (before Oracle transformation)
                # Note: We store Oracle format in validated fields, so we need to reconstruct
                # For now, we'll show the Oracle format in validated columns
                entity.entity_name_validated or entity.entity_name_original or '',
                entity.address1_validated or entity.address1_original or '',
                entity.address2_validated or entity.address2_original or '',
                entity.city_validated or entity.city_original or '',
                entity.state_validated or entity.state_original or '',
                entity.zip_validated or entity.zip_original or '',
                entity.country_validated or entity.country_original or '',
                float(entity.latitude) if entity.latitude else '',
                float(entity.longitude) if entity.longitude else '',
                
                # Oracle (same as validated since we transform in place)
                entity.entity_name_validated or '',
                entity.address1_validated or '',
                entity.address2_validated or '',
                entity.city_validated or '',
                entity.state_validated or '',
                entity.zip_validated or '',
                entity.country_validated or '',
                
                # Metadata
                float(entity.overall_confidence_score) if entity.overall_confidence_score else 0.0,
                entity.confidence_level or 'NONE',
                entity.record_status or 'PENDING',
                entity.validation_source or '',
                'YES' if entity.has_geocoding else 'NO',
                entity.validated_at.strftime('%Y-%m-%d %H:%M:%S') if entity.validated_at else '',
                
                # USPS
                entity.usps_delivery_line_1 or '',
                entity.usps_delivery_line_2 or '',
                entity.usps_last_line or ''
            ]
            
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        
        filename = f"{job.job_name}_Complete_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/oracle-only")
async def export_oracle_only(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Export only Oracle-formatted columns (for direct Oracle Fusion import)
    """
    try:
        job = db.query(ValidationJob).filter(
            ValidationJob.job_id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        entities = db.query(Entity).filter(
            Entity.job_id == job_id,
            Entity.record_status == 'READY'  # Only export READY records
        ).order_by(Entity.row_number).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Oracle Fusion standard headers
        headers = [
            'Entity Name',
            'Address Name',
            'Address Line 1',
            'Address Line 2',
            'Address Line 3',
            'City',
            'State',
            'Postal Code',
            'Country',
            'Latitude',
            'Longitude'
        ]
        
        writer.writerow(headers)
        
        for entity in entities:
            row = [
                entity.entity_name_validated or '',
                f"{entity.entity_name_original or 'Unknown'} - Main Address",
                entity.address1_validated or '',
                entity.address2_validated or '',
                '',  # Address Line 3
                entity.city_validated or '',
                entity.state_validated or '',
                entity.zip_validated or '',
                entity.country_validated or 'US',
                float(entity.latitude) if entity.latitude else '',
                float(entity.longitude) if entity.longitude else ''
            ]
            
            writer.writerow(row)
        
        output.seek(0)
        
        filename = f"{job.job_name}_Oracle_Ready_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
