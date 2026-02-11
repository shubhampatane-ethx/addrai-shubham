"""
BATCH PROCESSING VALIDATION TASK
REFACTORED: Supplier → Entity
Processes large files in configurable batches with auto-resume capability
"""
from celery import current_task
from backend.app.core.database import SessionLocal
from backend.app.models.models import ValidationJob, Entity
from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.services.oracle_transformer import OracleAddressTransformer
from backend.app.celery_app import celery_app
import logging
from datetime import datetime
from sqlalchemy import func

logger = logging.getLogger(__name__)

# CONFIGURATION
BATCH_SIZE = 500  # Process 500 records per batch
COMMIT_FREQUENCY = 50  # Commit every 50 records within a batch


@celery_app.task(bind=True, name='validate_entities_batch', time_limit=7200, soft_time_limit=7000)
def validate_entities_batch(self, job_id: str, batch_start: int = 0):
    """
    Process validation in batches to avoid timeout
    
    Args:
        job_id: UUID of the validation job
        batch_start: Row number to start from (for resume capability)
    """
    db = SessionLocal()
    
    try:
        # Get job
        job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Initialize validators
        osm_validator = OSMNominatimValidator()
        
        # Update job status
        if batch_start == 0:
            job.status = 'PROCESSING'
            job.started_at = datetime.utcnow()
        
        job.current_step = f'Batch processing from row {batch_start}'
        db.commit()
        
        # Get total count
        total_count = db.query(func.count(Entity.entity_id)).filter(
            Entity.job_id == job_id
        ).scalar()
        
        logger.info(f"[BATCH] Starting batch from row {batch_start} of {total_count}")
        
        # Calculate batch end
        batch_end = min(batch_start + BATCH_SIZE, total_count)
        
        # Get entities for this batch
        entities = db.query(Entity).filter(
            Entity.job_id == job_id,
            Entity.row_number >= batch_start,
            Entity.row_number < batch_end
        ).order_by(Entity.row_number).all()
        
        logger.info(f"[BATCH] Retrieved {len(entities)} entities for processing")
        
        # Process each entity
        processed = 0
        failed = 0
        
        for idx, entity in enumerate(entities, 1):
            try:
                logger.info(f"[{batch_start + idx}/{total_count}] Processing: {entity.entity_name_original}")
                
                # STAGE 2: OSM Validation
                osm_result = osm_validator.validate({
                    'address1': entity.address1_original,
                    'address2': entity.address2_original,
                    'city': entity.city_original,
                    'state': entity.state_original,
                    'zip': entity.zip_original,
                    'country': entity.country_original or 'US'
                })
                
                # Apply OSM results
                if osm_result and osm_result.get('success'):
                    validated = osm_result.get('validated_address', {})
                    metadata = osm_result.get('metadata', {})
                    
                    entity.entity_name_osm = entity.entity_name_original  # Name not validated by OSM
                    entity.address1_osm = validated.get('address1', entity.address1_original)
                    entity.address2_osm = validated.get('address2', entity.address2_original)
                    entity.city_osm = validated.get('city', entity.city_original)
                    entity.state_osm = validated.get('state', entity.state_original)
                    entity.zip_osm = validated.get('zip', entity.zip_original)
                    entity.country_osm = validated.get('country', entity.country_original or 'US')
                    entity.osm_source = osm_result.get('validation_source', 'OSM_Nominatim')
                    entity.fields_filled_by_osm = []
                    entity.fields_corrected_by_osm = []
                    entity.osm_corrections = {}
                    entity.latitude = validated.get('latitude')
                    entity.longitude = validated.get('longitude')
                    entity.has_geocoding = bool(entity.latitude and entity.longitude)
                else:
                    # OSM failed, use original data
                    entity.entity_name_osm = entity.entity_name_original
                    entity.address1_osm = entity.address1_original
                    entity.address2_osm = entity.address2_original
                    entity.city_osm = entity.city_original
                    entity.state_osm = entity.state_original
                    entity.zip_osm = entity.zip_original
                    entity.country_osm = entity.country_original or 'US'
                    entity.fields_filled_by_osm = []
                    entity.fields_corrected_by_osm = []
                    entity.osm_corrections = {}
                
                # STAGE 3: Oracle Transformation
                oracle_data = OracleAddressTransformer.transform_entity_address({
                    'entity_name_validated': entity.entity_name_osm,
                    'entity_name_original': entity.entity_name_original,
                    'address1_validated': entity.address1_osm,
                    'address1_original': entity.address1_original,
                    'address2_validated': entity.address2_osm,
                    'address2_original': entity.address2_original,
                    'address3_original': entity.address3_original,
                    'city_validated': entity.city_osm,
                    'city_original': entity.city_original,
                    'state_validated': entity.state_osm,
                    'state_original': entity.state_original,
                    'zip_validated': entity.zip_osm,
                    'zip_original': entity.zip_original,
                    'country_validated': entity.country_osm,
                    'country_original': entity.country_original
                })
                
                if oracle_data:
                    entity.entity_name_ora = oracle_data.get('oracle_entity_name')
                    entity.address1_ora = oracle_data.get('oracle_address1')
                    entity.address2_ora = oracle_data.get('oracle_address2')
                    entity.address3_ora = oracle_data.get('oracle_address3')
                    entity.city_ora = oracle_data.get('oracle_city')
                    entity.state_ora = oracle_data.get('oracle_state')
                    entity.zip_ora = oracle_data.get('oracle_zip')
                    entity.country_ora = oracle_data.get('oracle_country')
                    entity.fill_stage = 'oracle_transformed'
                else:
                    # Oracle failed, use OSM data
                    entity.entity_name_ora = entity.entity_name_osm
                    entity.address1_ora = entity.address1_osm
                    entity.address2_ora = entity.address2_osm
                    entity.address3_ora = None
                    entity.city_ora = entity.city_osm
                    entity.state_ora = entity.state_osm
                    entity.zip_ora = entity.zip_osm
                    entity.country_ora = entity.country_osm
                    entity.fill_stage = 'osm'
                
                # Set validated fields (for compatibility)
                entity.entity_name_validated = entity.entity_name_ora
                entity.address1_validated = entity.address1_ora
                entity.city_validated = entity.city_ora
                entity.state_validated = entity.state_ora
                entity.zip_validated = entity.zip_ora
                entity.country_validated = entity.country_ora
                
                # Create USPS formatted output from OSM result
                usps_formatted = osm_result.get('usps_formatted', {}) if osm_result and osm_result.get('success') else {}
                entity.usps_delivery_line_1 = usps_formatted.get('delivery_line_1', entity.address1_ora or '')
                entity.usps_last_line = usps_formatted.get('last_line', f"{entity.city_ora}, {entity.state_ora} {entity.zip_ora}".strip())
                entity.usps_formatted_full = usps_formatted.get('full', f"{entity.usps_delivery_line_1}\n{entity.usps_last_line}".strip())
                
                # Calculate confidence and set status
                # HIGH: OSM validated successfully
                # MEDIUM: No OSM but has complete Oracle data
                # LOW: Missing critical Oracle fields
                if osm_result and osm_result.get('success'):
                    # OSM validation succeeded
                    entity.confidence_level = 'HIGH'
                    entity.overall_confidence_score = 90.0 + (10.0 if entity.latitude else 0.0)
                    entity.record_status = 'READY'
                elif entity.entity_name_ora and entity.address1_ora and entity.city_ora:
                    # No OSM but has complete Oracle transformation
                    entity.confidence_level = 'MEDIUM'
                    entity.overall_confidence_score = 70.0
                    entity.record_status = 'READY'
                else:
                    # Missing critical Oracle fields
                    entity.confidence_level = 'LOW'
                    entity.overall_confidence_score = 40.0
                    entity.record_status = 'REVIEW'
                
                entity.validated_at = datetime.utcnow()
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing entity {entity.entity_id}: {str(e)}")
                entity.confidence_level = 'NONE'
                entity.record_status = 'FAILED'
                failed += 1
            
            # Commit every COMMIT_FREQUENCY records
            if idx % COMMIT_FREQUENCY == 0:
                db.commit()
                logger.info(f"[BATCH] Committed {idx} records")
                
                # Update job progress for UI visibility
                job.processed_records = idx
                job.progress_percentage = (idx / total_count) * 100
                job.current_step = f'Stage 2: OSM fill/correct ({idx}/{total_count})'
                
                # Update confidence counts
                high_conf = db.query(Entity).filter(
                    Entity.job_id == job_id,
                    Entity.confidence_level == 'HIGH'
                ).count()
                medium_conf = db.query(Entity).filter(
                    Entity.job_id == job_id,
                    Entity.confidence_level == 'MEDIUM'
                ).count()
                low_conf = db.query(Entity).filter(
                    Entity.job_id == job_id,
                    Entity.confidence_level == 'LOW'
                ).count()
                
                job.high_confidence = high_conf
                job.medium_confidence = medium_conf
                job.low_confidence = low_conf
                
                db.commit()
        
        # Final commit for this batch
        db.commit()
        logger.info(f"[BATCH] Batch complete: {processed} processed, {failed} failed")
        
        # Update job progress
        total_processed = batch_end
        job.processed_records = total_processed
        job.progress_percentage = (total_processed / total_count) * 100
        job.current_step = f'Stage 2: OSM fill/correct ({total_processed}/{total_count})'
        
        # Update stats
        high = db.query(func.count(Entity.entity_id)).filter(
            Entity.job_id == job_id,
            Entity.confidence_level == 'HIGH'
        ).scalar()
        
        medium = db.query(func.count(Entity.entity_id)).filter(
            Entity.job_id == job_id,
            Entity.confidence_level == 'MEDIUM'
        ).scalar()
        
        low = db.query(func.count(Entity.entity_id)).filter(
            Entity.job_id == job_id,
            Entity.confidence_level == 'LOW'
        ).scalar()
        
        failed_total = db.query(func.count(Entity.entity_id)).filter(
            Entity.job_id == job_id,
            Entity.record_status == 'FAILED'
        ).scalar()
        
        job.high_confidence = high
        job.medium_confidence = medium
        job.low_confidence = low
        job.failed_records = failed_total
        
        db.commit()
        
        # Check if more batches needed
        if batch_end < total_count:
            logger.info(f"[BATCH] Scheduling next batch from row {batch_end}")
            # Schedule next batch
            validate_entities_batch.apply_async(
                args=[job_id, batch_end],
                countdown=2  # Start next batch in 2 seconds
            )
        else:
            # All done!
            logger.info(f"[BATCH] ALL BATCHES COMPLETE!")
            job.status = 'COMPLETED'
            job.current_step = f'Stage 2: OSM fill/correct ({total_count}/{total_count})'
            job.completed_at = datetime.utcnow()
            db.commit()
        
        return {
            'batch_start': batch_start,
            'batch_end': batch_end,
            'processed': processed,
            'failed': failed,
            'total_progress': total_processed,
            'total_count': total_count,
            'more_batches': batch_end < total_count
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        db.rollback()
        
        # Update job to failed state
        try:
            job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
            if job:
                job.status = 'FAILED'
                job.current_step = f'Error at row {batch_start}: {str(e)}'
                db.commit()
        except:
            pass
        
        raise
        
    finally:
        db.close()


@celery_app.task(bind=True, name='resume_validation_batch')
def resume_validation_batch(self, job_id: str):
    """
    Resume a failed/stuck validation from where it left off
    """
    db = SessionLocal()
    
    try:
        # Find last processed row
        max_row = db.query(func.max(Entity.row_number)).filter(
            Entity.job_id == job_id,
            Entity.validated_at.isnot(None)
        ).scalar()
        
        start_row = (max_row or 0) + 1
        
        logger.info(f"[RESUME] Resuming from row {start_row}")
        
        # Start batch processing from that row
        return validate_entities_batch.apply_async(args=[job_id, start_row])
        
    finally:
        db.close()
