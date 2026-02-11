"""
Jobs Export API - 3-Stage CSV Export with Confidence Filtering
REFACTORED: Supplier → Entity
Exports: Original → OSM → Oracle stages with optional confidence filter
Returns Oracle data (final production output)
NO AUTH REQUIRED - Compatible with existing setup
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
import csv
import io
from datetime import datetime
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{job_id}/results")
async def get_job_results(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get validation results for display in ResultsDialog
    
    Returns Oracle-transformed data (final production-ready output)
    """
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    entities = db.query(Entity).filter(
        Entity.job_id == job_id
    ).order_by(Entity.row_number).all()
    
    results = []
    for entity in entities:
        # Build Oracle address for display (final, production-ready format)
        oracle_address_parts = []
        if entity.address1_ora:
            oracle_address_parts.append(entity.address1_ora)
        if entity.address2_ora:
            oracle_address_parts.append(entity.address2_ora)
        oracle_address = ', '.join(oracle_address_parts) if oracle_address_parts else None
        
        # Build original address for comparison
        original_address_parts = []
        if entity.address1_original:
            original_address_parts.append(entity.address1_original)
        if entity.address2_original:
            original_address_parts.append(entity.address2_original)
        original_address = ', '.join(original_address_parts) if original_address_parts else None
        
        results.append({
            'entity_name': entity.entity_name_original or entity.entity_name_ora or entity.entity_name_osm,
            'original_address': original_address or entity.address1_original,
            
            # Prefer Oracle (final output) over OSM (intermediate)
            'oracle_address': oracle_address,  # Dedicated Oracle field
            'validated_address': entity.address1_ora or entity.address1_osm,  # Oracle first!
            'city': entity.city_ora or entity.city_osm,  # Oracle first!
            'state': entity.state_ora or entity.state_osm,  # Oracle first!
            'postal_code': entity.zip_ora or entity.zip_osm,  # Oracle first!
            
            # Metadata
            'confidence_level': entity.confidence_level,
            'confidence_score': entity.overall_confidence_score,
            'match_score': entity.overall_confidence_score / 100 if entity.overall_confidence_score else 0,
            'record_status': entity.record_status,
            'has_geocoding': entity.has_geocoding,
            'latitude': float(entity.latitude) if entity.latitude else None,
            'longitude': float(entity.longitude) if entity.longitude else None
        })
    
    return {'results': results}


@router.get("/{job_id}/export")
async def export_job_results(
    job_id: str,
    format: str = Query('3stage', regex='^(3stage|oracle_only|original_only)$'),
    confidence: str = Query(None, regex='^(high|medium|low)$'),
    db: Session = Depends(get_db)
):
    """
    Export validation results with optional confidence filtering
    
    Args:
        job_id: Job ID
        format: Export format (3stage, oracle_only, original_only)
        confidence: Filter by confidence level (high, medium, low, or None for all)
    
    Returns:
        CSV file download
    """
    logger.info(f"Exporting job {job_id}, format={format}, confidence={confidence}")
    
    # Get job
    job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build query
    query = db.query(Entity).filter(Entity.job_id == job_id)
    
    # Apply confidence filter if specified
    if confidence:
        confidence_upper = confidence.upper()
        query = query.filter(Entity.confidence_level == confidence_upper)
        logger.info(f"Filtering by confidence: {confidence_upper}")
    
    # Get entities (ordered by row number)
    entities = query.order_by(Entity.row_number).all()
    
    logger.info(f"Exporting {len(entities)} records")
    
    # Generate CSV based on format
    if format == '3stage':
        csv_data = generate_3stage_export(entities)
        format_suffix = "3stage"
    elif format == 'oracle_only':
        csv_data = generate_oracle_export(entities)
        format_suffix = "oracle"
    else:
        csv_data = generate_original_export(entities)
        format_suffix = "original"
    
    # Build filename
    confidence_suffix = f"_{confidence.lower()}" if confidence else ""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"validation_{format_suffix}{confidence_suffix}_{job.job_name}_{timestamp}.csv"
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(csv_data.encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def generate_3stage_export(entities) -> str:
    """
    Generate complete 3-stage CSV export
    Shows: Original → OSM → Oracle transformations
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers - All 3 stages
    headers = [
        # STAGE 1: ORIGINAL
        'row_number',
        'entity_name_original',
        'address1_original',
        'address2_original',
        'city_original',
        'state_original',
        'zip_original',
        'country_original',
        
        # STAGE 2: OSM FILLED/CORRECTED
        'entity_name_osm',
        'address1_osm',
        'address2_osm',
        'city_osm',
        'state_osm',
        'zip_osm',
        'zip4_osm',
        'country_osm',
        'osm_source',
        'latitude',
        'longitude',
        'fields_filled_by_osm',
        'fields_corrected_by_osm',
        'fill_percentage',
        'correction_percentage',
        
        # STAGE 3: ORACLE TRANSFORMED
        'entity_name_ora',
        'address1_ora',
        'address2_ora',
        'address3_ora',
        'city_ora',
        'state_ora',
        'zip_ora',
        'country_ora',
        
        # METADATA
        'confidence_level',
        'confidence_score',
        'record_status',
        'has_geocoding',
        'is_po_box',
        'validated_at',
        'corrections_json'
    ]
    
    writer.writerow(headers)
    
    # Data rows
    for entity in entities:
        # Handle array fields safely
        fields_filled = ', '.join(entity.fields_filled_by_osm or []) if entity.fields_filled_by_osm else ''
        fields_corrected = ', '.join(entity.fields_corrected_by_osm or []) if entity.fields_corrected_by_osm else ''
        corrections_json = json.dumps(entity.osm_corrections or {}) if entity.osm_corrections else ''
        
        row = [
            # ORIGINAL
            entity.row_number or '',
            entity.entity_name_original or '',
            entity.address1_original or '',
            entity.address2_original or '',
            entity.city_original or '',
            entity.state_original or '',
            entity.zip_original or '',
            entity.country_original or 'US',
            
            # OSM
            entity.entity_name_osm or '',
            entity.address1_osm or '',
            entity.address2_osm or '',
            entity.city_osm or '',
            entity.state_osm or '',
            entity.zip_osm or '',
            entity.zip4_osm or '',
            entity.country_osm or '',
            entity.osm_source or '',
            entity.latitude or '',
            entity.longitude or '',
            fields_filled,
            fields_corrected,
            entity.fill_percentage or 0,
            entity.correction_percentage or 0,
            
            # ORACLE
            entity.entity_name_ora or '',
            entity.address1_ora or '',
            entity.address2_ora or '',
            entity.address3_ora or '',
            entity.city_ora or '',
            entity.state_ora or '',
            entity.zip_ora or '',
            entity.country_ora or '',
            
            # METADATA
            entity.confidence_level or '',
            entity.overall_confidence_score or 0,
            entity.record_status or '',
            'Yes' if entity.has_geocoding else 'No',
            'Yes' if entity.is_po_box else 'No',
            entity.validated_at.strftime('%Y-%m-%d %H:%M:%S') if entity.validated_at else '',
            corrections_json
        ]
        
        writer.writerow(row)
    
    return output.getvalue()


def generate_oracle_export(entities) -> str:
    """
    Generate Oracle-only CSV export
    For direct import into Oracle Fusion
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Oracle Fusion headers (uppercase)
    headers = [
        'ENTITY_NAME',
        'ADDRESS_LINE_1',
        'ADDRESS_LINE_2',
        'ADDRESS_LINE_3',
        'CITY',
        'STATE',
        'POSTAL_CODE',
        'COUNTRY',
        'LATITUDE',
        'LONGITUDE',
        'VALIDATION_STATUS',
        'CONFIDENCE_LEVEL',
        'QUALITY_SCORE'
    ]
    
    writer.writerow(headers)
    
    # Data rows - Oracle format only
    for entity in entities:
        row = [
            entity.entity_name_ora or '',
            entity.address1_ora or '',
            entity.address2_ora or '',
            entity.address3_ora or '',
            entity.city_ora or '',
            entity.state_ora or '',
            entity.zip_ora or '',
            entity.country_ora or 'US',
            entity.latitude or '',
            entity.longitude or '',
            entity.record_status or 'PENDING',
            entity.confidence_level or 'NONE',
            entity.overall_confidence_score or 0
        ]
        
        writer.writerow(row)
    
    return output.getvalue()


def generate_original_export(entities) -> str:
    """
    Generate original-only CSV export
    For comparison or record-keeping
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        'row_number',
        'entity_name',
        'address1',
        'address2',
        'city',
        'state',
        'zip',
        'country'
    ]
    
    writer.writerow(headers)
    
    for entity in entities:
        row = [
            entity.row_number or '',
            entity.entity_name_original or '',
            entity.address1_original or '',
            entity.address2_original or '',
            entity.city_original or '',
            entity.state_original or '',
            entity.zip_original or '',
            entity.country_original or 'US'
        ]
        
        writer.writerow(row)
    
    return output.getvalue()
