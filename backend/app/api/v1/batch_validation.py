"""
Batch Validation Endpoint
REFACTORED: Supplier → Entity
Handle validation of address batches (5 records at a time)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.services.oracle_transformer import OracleAddressTransformer
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class BatchValidationRequest(BaseModel):
    job_id: str
    entity_ids: List[str]
    validator: str = 'openstreetmap'


@router.post("/batch")
async def validate_batch(
    request: BatchValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a batch of entities (recommended: 5 at a time)
    Includes entity name validation and all field completion
    """
    try:
        # Get job
        job = db.query(ValidationJob).filter(
            ValidationJob.job_id == request.job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Update job status
        if job.status == 'UPLOADED':
            job.status = 'PROCESSING'
            job.started_at = datetime.utcnow()
            db.commit()
        
        # Get entities in this batch
        entities = db.query(Entity).filter(
            Entity.entity_id.in_(request.entity_ids),
            Entity.job_id == request.job_id
        ).all()
        
        if not entities:
            raise HTTPException(status_code=404, detail="No entities found in batch")
        
        # Initialize validator
        validator = OSMNominatimValidator()
        
        # Process each entity
        results = []
        for entity in entities:
            try:
                # Prepare address data (including entity name)
                address_data = {
                    'entity_name': entity.entity_name_original,
                    'address1': entity.address1_original,
                    'address2': entity.address2_original or '',
                    'city': entity.city_original,
                    'state': entity.state_original,
                    'zip': entity.zip_original,
                    'country': entity.country_original or 'US'
                }
                
                # Validate address (OSM will help complete missing fields)
                result = validator.validate(address_data)
                
                if result['success']:
                    validated = result['validated_address']
                    usps_formatted = result.get('usps_formatted', {})
                    
                    # Update validated fields
                    entity.entity_name_validated = validated.get('entity_name', entity.entity_name_original)
                    entity.address1_validated = validated.get('address1')
                    entity.address2_validated = validated.get('address2', '')
                    entity.city_validated = validated.get('city')
                    entity.state_validated = validated.get('state')
                    entity.zip_validated = validated.get('zip')
                    entity.country_validated = validated.get('country', 'US')
                    
                    # Geocoding
                    lat = validated.get('latitude')
                    lng = validated.get('longitude')
                    entity.latitude = float(lat) if lat else None
                    entity.longitude = float(lng) if lng else None
                    entity.has_geocoding = (entity.latitude is not None and entity.longitude is not None)
                    
                    # USPS formatting
                    entity.usps_delivery_line_1 = usps_formatted.get('delivery_line_1', validated.get('address1'))
                    entity.usps_delivery_line_2 = usps_formatted.get('delivery_line_2', '')
                    entity.usps_last_line = usps_formatted.get('last_line', f"{validated.get('city')}, {validated.get('state')} {validated.get('zip')}")
                    entity.usps_formatted_full = usps_formatted.get('full', f"{validated.get('address1')}\n{validated.get('city')}, {validated.get('state')} {validated.get('zip')}")
                    
                    # Confidence
                    confidence = result.get('confidence_score', 0)
                    entity.overall_confidence_score = float(confidence) if confidence else 0.0
                    entity.validation_source = result.get('validation_source', 'OSM_Nominatim')
                    entity.validated_at = datetime.utcnow()
                    
                    # ORACLE TRANSFORMATION
                    oracle_data = OracleAddressTransformer.transform_entity_address({
                        'entity_name_validated': entity.entity_name_validated,
                        'entity_name_original': entity.entity_name_original,
                        'address1_validated': entity.address1_validated,
                        'address1_original': entity.address1_original,
                        'address2_validated': entity.address2_validated,
                        'address2_original': entity.address2_original,
                        'city_validated': entity.city_validated,
                        'city_original': entity.city_original,
                        'state_validated': entity.state_validated,
                        'state_original': entity.state_original,
                        'zip_validated': entity.zip_validated,
                        'zip_original': entity.zip_original,
                        'country_validated': entity.country_validated,
                        'country_original': entity.country_original
                    })
                    
                    # Store Oracle format
                    entity.entity_name_validated = oracle_data['oracle_entity_name']
                    entity.address1_validated = oracle_data['oracle_address1']
                    entity.address2_validated = oracle_data['oracle_address2']
                    entity.city_validated = oracle_data['oracle_city']
                    entity.state_validated = oracle_data['oracle_state']
                    entity.zip_validated = oracle_data['oracle_zip']
                    entity.country_validated = oracle_data['oracle_country']
                    
                    # Set confidence level and status
                    if confidence >= 90:
                        entity.confidence_level = 'HIGH'
                        entity.record_status = 'READY'
                    elif confidence >= 70:
                        entity.confidence_level = 'MEDIUM'
                        entity.record_status = 'REVIEW'
                    else:
                        entity.confidence_level = 'LOW'
                        entity.record_status = 'REVIEW'
                    
                    results.append({
                        'entity_id': str(entity.entity_id),
                        'status': 'success',
                        'confidence': confidence
                    })
                else:
                    # Validation failed
                    entity.confidence_level = 'NONE'
                    entity.record_status = 'FAILED'
                    entity.overall_confidence_score = 0
                    
                    results.append({
                        'entity_id': str(entity.entity_id),
                        'status': 'failed',
                        'error': result.get('error')
                    })
                
            except Exception as e:
                logger.error(f"Error processing entity {entity.entity_id}: {str(e)}")
                entity.confidence_level = 'NONE'
                entity.record_status = 'FAILED'
                results.append({
                    'entity_id': str(entity.entity_id),
                    'status': 'error',
                    'error': str(e)
                })
        
        # Update job statistics
        total_entities = db.query(Entity).filter(
            Entity.job_id == request.job_id
        ).count()
        
        processed = db.query(Entity).filter(
            Entity.job_id == request.job_id,
            Entity.validated_at.isnot(None)
        ).count()
        
        high_conf = db.query(Entity).filter(
            Entity.job_id == request.job_id,
            Entity.confidence_level == 'HIGH'
        ).count()
        
        medium_conf = db.query(Entity).filter(
            Entity.job_id == request.job_id,
            Entity.confidence_level == 'MEDIUM'
        ).count()
        
        low_conf = db.query(Entity).filter(
            Entity.job_id == request.job_id,
            Entity.confidence_level == 'LOW'
        ).count()
        
        failed = db.query(Entity).filter(
            Entity.job_id == request.job_id,
            Entity.record_status == 'FAILED'
        ).count()
        
        job.processed_records = processed
        job.high_confidence = high_conf
        job.medium_confidence = medium_conf
        job.low_confidence = low_conf
        job.failed_records = failed
        job.progress_percentage = (processed / total_entities * 100) if total_entities > 0 else 0
        
        # Mark as completed if all done
        if processed >= total_entities:
            job.status = 'COMPLETED'
            job.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            'status': 'success',
            'batch_size': len(entities),
            'results': results,
            'job_progress': {
                'processed': processed,
                'total': total_entities,
                'percentage': job.progress_percentage
            }
        }
        
    except Exception as e:
        logger.error(f"Batch validation error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
