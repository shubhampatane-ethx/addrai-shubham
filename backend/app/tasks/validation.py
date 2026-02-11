"""
Celery Tasks - Address Validation with Smart Correction
REFACTORED: Supplier → Entity
3-STAGE VALIDATION:
1. Original data (as uploaded)
2. OSM Fill & Correct (fills missing AND corrects wrong fields)
3. Oracle Transform (Oracle Fusion format)
"""
from backend.app.celery_app import celery_app
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.models import ValidationJob, Entity

from backend.app.services.bifrost_service import bifrost_validate

from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.services.oracle_transformer import OracleAddressTransformer
from backend.app.services.metrics_calculator import MetricsCalculator
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)


# ============================================
# SMART VALIDATOR - Fills + Corrects
# ============================================

class SmartValidator:
    """
    Smart validation: Fills missing AND corrects wrong fields
    Tracks what was filled vs corrected separately
    """
    
    def __init__(self):
        self.us_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        }
    
    def validate_and_fill(self, entity, osm_validated_address: dict, osm_address_components: dict):
        """
        Main validation: Fills missing AND corrects wrong fields
        
        Args:
            entity: Entity database object
            osm_validated_address: Dict from OSM with {address1, city, state, zip, latitude, longitude}
            osm_address_components: Raw OSM address components
        
        Returns:
            Dict with filled and corrected field lists
        """
        fields_filled = []
        fields_corrected = []
        corrections = {}
        
        # ENTITY NAME
        entity_name_result = self._process_field(
            'entity_name',
            entity.entity_name_original,
            osm_address_components.get('name') or osm_address_components.get('shop'),
            self._is_valid_entity_name
        )
        entity.entity_name_osm = entity_name_result['value']
        if entity_name_result['action'] == 'filled':
            fields_filled.append('entity_name')
        elif entity_name_result['action'] == 'corrected':
            fields_corrected.append('entity_name')
            corrections['entity_name'] = entity_name_result['correction']
        
        # ADDRESS1
        address1_result = self._process_field(
            'address1',
            entity.address1_original,
            osm_validated_address.get('address1'),
            self._is_valid_address
        )
        entity.address1_osm = address1_result['value']
        if address1_result['action'] == 'filled':
            fields_filled.append('address1')
        elif address1_result['action'] == 'corrected':
            fields_corrected.append('address1')
            corrections['address1'] = address1_result['correction']
        
        # CITY
        city_result = self._process_field(
            'city',
            entity.city_original,
            osm_validated_address.get('city'),
            self._is_valid_city
        )
        entity.city_osm = city_result['value']
        if city_result['action'] == 'filled':
            fields_filled.append('city')
        elif city_result['action'] == 'corrected':
            fields_corrected.append('city')
            corrections['city'] = city_result['correction']
        
        # STATE
        state_result = self._process_field(
            'state',
            entity.state_original,
            osm_validated_address.get('state'),
            self._is_valid_state
        )
        entity.state_osm = state_result['value']
        if state_result['action'] == 'filled':
            fields_filled.append('state')
        elif state_result['action'] == 'corrected':
            fields_corrected.append('state')
            corrections['state'] = state_result['correction']
        
        # ZIP
        zip_result = self._process_field(
            'zip',
            entity.zip_original,
            osm_validated_address.get('zip'),
            self._is_valid_zip
        )
        entity.zip_osm = zip_result['value']
        if zip_result['action'] == 'filled':
            fields_filled.append('zip')
        elif zip_result['action'] == 'corrected':
            fields_corrected.append('zip')
            corrections['zip'] = zip_result['correction']
        
        # COUNTRY (always use OSM or default)
        entity.country_osm = entity.country_original or osm_validated_address.get('country', 'US')
        
        # GEOCODING (always from OSM)
        entity.latitude = osm_validated_address.get('latitude')
        entity.longitude = osm_validated_address.get('longitude')
        entity.has_geocoding = bool(entity.latitude and entity.longitude)
        
        # METADATA
        entity.osm_source = 'OSM_Nominatim'
        entity.fields_filled_by_osm = fields_filled
        entity.fields_corrected_by_osm = fields_corrected
        entity.osm_corrections = corrections
        
        # PERCENTAGES
        total_fields = 6  # entity_name, address1, city, state, zip, country
        entity.fill_percentage = (len(fields_filled) / total_fields) * 100
        entity.correction_percentage = (len(fields_corrected) / total_fields) * 100
        entity.fill_stage = 'osm_filled'
        
        return {
            'filled': fields_filled,
            'corrected': fields_corrected,
            'corrections': corrections
        }
    
    def _process_field(self, field_name: str, original_value: str, osm_value: str, validator_func):
        """
        Process a single field: fill if missing, correct if invalid
        
        Returns: {value, action, correction}
        """
        # Missing - fill
        if not original_value or original_value.strip() == '':
            return {
                'value': osm_value or original_value or '',
                'action': 'filled' if osm_value else 'kept',
                'correction': None
            }
        
        # Invalid - correct
        if not validator_func(original_value):
            return {
                'value': osm_value or original_value,
                'action': 'corrected' if osm_value else 'kept',
                'correction': {
                    'old': original_value,
                    'new': osm_value,
                    'reason': f'Invalid {field_name} format'
                } if osm_value else None
            }
        
        # Valid - keep original
        return {
            'value': original_value,
            'action': 'kept',
            'correction': None
        }
    
    def _is_valid_entity_name(self, entity_name: str) -> bool:
        """Check if entity name is valid"""
        if not entity_name or len(entity_name.strip()) < 2:
            return False
        if re.match(r'^[0-9]+$', entity_name):  # Only numbers
            return False
        return True
    
    def _is_valid_address(self, address: str) -> bool:
        """Check if address is valid"""
        if not address or len(address.strip()) < 3:
            return False
        if re.match(r'^[0-9\s]+$', address):  # Only numbers and spaces
            return False
        return True
    
    def _is_valid_city(self, city: str) -> bool:
        """Check if city is valid"""
        if not city or len(city.strip()) < 2:
            return False
        if re.match(r'^[0-9]+$', city):  # Only numbers
            return False
        return True
    
    def _is_valid_state(self, state: str) -> bool:
        """Check if state is valid US state code"""
        if not state:
            return False
        state_upper = state.strip().upper()
        return state_upper in self.us_states
    
    def _is_valid_zip(self, zip_code: str) -> bool:
        """Check if ZIP code is valid"""
        if not zip_code:
            return False
        # US ZIP: 12345 or 12345-6789
        return bool(re.match(r'^\d{5}(-\d{4})?$', zip_code.strip()))


# ============================================
# CELERY TASK
# ============================================

@celery_app.task(bind=True, name='validate_entities_task')
def validate_entities_task(self, job_id: str, validator_type: str = "openstreetmap", openai_prompt: str = ""):
    """
    Main validation task - Process all entities for a job
    REFACTORED: Supplier → Entity
    
    Args:
        job_id: UUID of validation job
        validator_type: Type of validator to use (openstreetmap, google, etc.)
    """
    db = SessionLocal()
    job = None
    use_bifrost = validator_type in ("bifrost", "openai")


    try:
        logger.info(f"╔══════════════════════════════════════════╗")
        logger.info(f"║ Starting Validation: {job_id[:8]}...        ║")
        logger.info(f"╚══════════════════════════════════════════╝")
        
        # Get job
        job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Get entities
        entities = db.query(Entity).filter(Entity.job_id == job_id).order_by(Entity.row_number).all()
        total = len(entities)
        
        logger.info(f"Processing {total} entities...")
        
        # Initialize
        job.status = 'PROCESSING'
        job.started_at = datetime.utcnow()
        job.current_step = 'Stage 1: Original data loaded'
        db.commit()
        
        # Initialize validator
        osm_validator = None
        if not use_bifrost:
            osm_validator = OSMNominatimValidator()

        smart_validator = SmartValidator()

        
        # Counters
        processed = 0
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        failed = 0
        total_filled = 0
        total_corrected = 0
        
        # Process each entity
        for idx, entity in enumerate(entities, 1):
            try:
                logger.info(f"[{idx}/{total}] Processing: {entity.entity_name_original}")
                
                # STAGE 2: OSM Validation
                # STAGE 2: VALIDATION
                job.current_step = f"Stage 2: {'BiFrost' if use_bifrost else 'OSM'} validation ({idx}/{total})"

                if use_bifrost:
                    bifrost_result = bifrost_validate(
                        f"{entity.entity_name_original}, "
                        f"{entity.address1_original}, "
                        f"{entity.city_original}, "         
                        f"{entity.state_original}, "
                        f"{entity.zip_original}, "
                        f"{entity.country_original or 'US'}",
                        user_prompt=openai_prompt
                    )


                    osm_result = {
                        "success": True,
                        "validated_address": {
                            "address1": bifrost_result.get("normalized_address"),
                            "city": bifrost_result.get("city"),
                            "state": bifrost_result.get("state"),
                            "zip": bifrost_result.get("postal_code"),
                            "country": bifrost_result.get("country", "US"),
                            "latitude": None,
                            "longitude": None
                        },
                        "metadata": {
                            "confidence_score": bifrost_result.get("confidence_score", 0)
                        }
                    }
                else:
                    osm_result = osm_validator.validate({
                        'entity_name': entity.entity_name_original,
                        'address1': entity.address1_original,
                        'address2': entity.address2_original,
                        'city': entity.city_original,
                        'state': entity.state_original,
                        'zip': entity.zip_original,
                        'country': entity.country_original or 'US'
                    })

                
                if osm_result.get('success'):
                    # Smart validation - fills and corrects
                    validation_result = smart_validator.validate_and_fill(
                        entity,
                        osm_result.get('validated_address', {}),
                        osm_result.get('metadata', {})
                    )
                    
                    total_filled += len(validation_result.get('filled', []))
                    total_corrected += len(validation_result.get('corrected', []))
                    
                    # STAGE 3: Oracle Transformation
                    job.current_step = f'Stage 3: Oracle transform ({idx}/{total})'
                    
                    oracle_data = OracleAddressTransformer.transform_entity_address({
                        'entity_name_validated': entity.entity_name_osm,
                        'entity_name_original': entity.entity_name_original,
                        'address1_validated': entity.address1_osm,
                        'address1_original': entity.address1_original,
                        'address2_validated': entity.address2_osm,
                        'address2_original': entity.address2_original,
                        'city_validated': entity.city_osm,
                        'city_original': entity.city_original,
                        'state_validated': entity.state_osm,
                        'state_original': entity.state_original,
                        'zip_validated': entity.zip_osm,
                        'zip_original': entity.zip_original,
                        'country_validated': entity.country_osm,
                        'country_original': entity.country_original
                    })
                    
                    # Store Oracle-formatted data
                    entity.entity_name_ora = oracle_data['oracle_entity_name']
                    entity.address1_ora = oracle_data['oracle_address1']
                    entity.address2_ora = oracle_data['oracle_address2']
                    entity.city_ora = oracle_data['oracle_city']
                    entity.state_ora = oracle_data['oracle_state']
                    entity.zip_ora = oracle_data['oracle_zip']
                    entity.country_ora = oracle_data['oracle_country']
                    
                    # Also set legacy validated fields for backward compatibility
                    entity.entity_name_validated = oracle_data['oracle_entity_name']
                    entity.address1_validated = oracle_data['oracle_address1']
                    entity.city_validated = oracle_data['oracle_city']
                    entity.state_validated = oracle_data['oracle_state']
                    entity.zip_validated = oracle_data['oracle_zip']
                    entity.country_validated = oracle_data['oracle_country']
                    
                    entity.fill_stage = 'oracle_transformed'
                    
                    # USPS formatting (from existing logic)
                    usps_formatted = osm_result.get('usps_formatted', {})
                    entity.usps_delivery_line_1 = usps_formatted.get('delivery_line_1', entity.address1_ora)
                    entity.usps_last_line = usps_formatted.get('last_line', f"{entity.city_ora}, {entity.state_ora} {entity.zip_ora}")
                    entity.usps_formatted_full = usps_formatted.get('full', f"{entity.address1_ora}\n{entity.city_ora}, {entity.state_ora} {entity.zip_ora}")
                    
                    # CALCULATE CONFIDENCE
                    confidence = _calculate_confidence(entity, validation_result)
                    entity.overall_confidence_score = confidence
                    entity.validation_source = 'BIFROST' if use_bifrost else 'OSM_Nominatim'

                    entity.validated_at = datetime.utcnow()
                    
                    # Set confidence level and status
                    if confidence >= 80:
                        entity.confidence_level = 'HIGH'
                        entity.record_status = 'READY'
                        high_confidence += 1
                    elif confidence >= 65:
                        entity.confidence_level = 'MEDIUM'
                        entity.record_status = 'REVIEW'
                        medium_confidence += 1
                    else:
                        entity.confidence_level = 'LOW'
                        entity.record_status = 'REVIEW'
                        low_confidence += 1
                    
                    # METRICS
                    try:
                        MetricsCalculator.update_entity_metrics(entity)
                    except Exception as e:
                        logger.error(f"Error calculating metrics: {str(e)}")
                    
                    logger.info(f"  ✅ Complete: {entity.confidence_level} ({confidence:.1f}%)")
                
                else:
                    # Validation failed - check if it's a PO Box or has usable data
                    metadata = osm_result.get('metadata', {})
                    error_msg = osm_result.get('error', '')
                    
                    # Check if this is a PO Box (can't be geocoded)
                    if metadata.get('is_po_box') or 'PO Box' in error_msg:
                        # PO BOX HANDLING
                        entity.is_po_box = True
                        entity.requires_manual_review = True
                        entity.validation_source = 'ORIGINAL_DATA'
                        
                        # Check completeness of PO Box data
                        has_complete_data = all([
                            entity.address1_original,
                            entity.city_original,
                            entity.state_original,
                            entity.zip_original
                        ])
                        
                        if has_complete_data:
                            # COMPLETE PO Box → MEDIUM confidence
                            entity.confidence_level = 'MEDIUM'
                            entity.record_status = 'REVIEW'
                            entity.overall_confidence_score = 70
                            medium_confidence += 1
                            logger.warning(f"  ⚠️  Complete PO Box - MEDIUM confidence")
                        else:
                            # INCOMPLETE PO Box → LOW confidence
                            entity.confidence_level = 'LOW'
                            entity.record_status = 'REVIEW'
                            entity.overall_confidence_score = 40
                            low_confidence += 1
                            logger.warning(f"  ⚠️  Incomplete PO Box - LOW confidence")
                        
                        # Preserve original data for PO Boxes
                        validated_addr = osm_result.get('validated_address', {})
                        entity.address1_validated = validated_addr.get('address1', entity.address1_original)
                        entity.city_validated = validated_addr.get('city', entity.city_original)
                        entity.state_validated = validated_addr.get('state', entity.state_original)
                        entity.zip_validated = validated_addr.get('zip', entity.zip_original)
                        entity.country_validated = validated_addr.get('country', entity.country_original or 'US')
                        
                        # Apply Oracle transformation to original data
                        oracle_data = OracleAddressTransformer.transform_entity_address({
                            'entity_name_validated': entity.entity_name_original,
                            'entity_name_original': entity.entity_name_original,
                            'address1_validated': entity.address1_original,
                            'address1_original': entity.address1_original,
                            'address2_validated': entity.address2_original or '',
                            'address2_original': entity.address2_original or '',
                            'city_validated': entity.city_original,
                            'city_original': entity.city_original,
                            'state_validated': entity.state_original,
                            'state_original': entity.state_original,
                            'zip_validated': entity.zip_original,
                            'zip_original': entity.zip_original,
                            'country_validated': entity.country_original or 'US',
                            'country_original': entity.country_original or 'US'
                        })
                        
                        # Store Oracle-formatted PO Box data
                        entity.entity_name_ora = oracle_data['oracle_entity_name']
                        entity.address1_ora = oracle_data['oracle_address1']
                        entity.address2_ora = oracle_data['oracle_address2']
                        entity.city_ora = oracle_data['oracle_city']
                        entity.state_ora = oracle_data['oracle_state']
                        entity.zip_ora = oracle_data['oracle_zip']
                        entity.country_ora = oracle_data['oracle_country']
                        
                        entity.fill_stage = 'oracle_transformed'
                        
                    else:
                        # NOT A PO BOX - Regular validation failure
                        # Calculate completeness score to determine if data is usable
                        
                        completeness = 0
                        if entity.address1_original: completeness += 25
                        if entity.city_original: completeness += 25
                        if entity.state_original: completeness += 25
                        if entity.zip_original: completeness += 25
                        
                        # All records get LOW confidence (no more FAILED status)
                        # Score reflects data completeness
                        entity.confidence_level = 'LOW'
                        entity.record_status = 'REVIEW'
                        entity.overall_confidence_score = max(completeness, 20)  # Minimum 20
                        entity.requires_manual_review = True
                        entity.validation_source = 'ORIGINAL_DATA'
                        low_confidence += 1
                        
                        # Apply Oracle transformation to whatever data we have
                        try:
                            oracle_data = OracleAddressTransformer.transform_entity_address({
                                'entity_name_validated': entity.entity_name_original or '',
                                'entity_name_original': entity.entity_name_original or '',
                                'address1_validated': entity.address1_original or '',
                                'address1_original': entity.address1_original or '',
                                'address2_validated': entity.address2_original or '',
                                'address2_original': entity.address2_original or '',
                                'city_validated': entity.city_original or '',
                                'city_original': entity.city_original or '',
                                'state_validated': entity.state_original or '',
                                'state_original': entity.state_original or '',
                                'zip_validated': entity.zip_original or '',
                                'zip_original': entity.zip_original or '',
                                'country_validated': entity.country_original or 'US',
                                'country_original': entity.country_original or 'US'
                            })
                            
                            entity.entity_name_ora = oracle_data['oracle_entity_name']
                            entity.address1_ora = oracle_data['oracle_address1']
                            entity.address2_ora = oracle_data['oracle_address2']
                            entity.city_ora = oracle_data['oracle_city']
                            entity.state_ora = oracle_data['oracle_state']
                            entity.zip_ora = oracle_data['oracle_zip']
                            entity.country_ora = oracle_data['oracle_country']
                            
                            entity.fill_stage = 'oracle_transformed'
                        except Exception as e:
                            logger.error(f"  ❌ Oracle transformation failed for incomplete data: {str(e)}")
                            entity.fill_stage = 'failed'
                        
                        if completeness >= 75:
                            logger.warning(f"  ⚠️  Validation failed but has {completeness}% data - LOW confidence")
                        else:
                            logger.warning(f"  ⚠️  Incomplete data ({completeness}%) - LOW confidence")
                
                
                processed += 1
                
                # Update progress every 10 records
                if processed % 10 == 0:
                    progress = (processed / total) * 100
                    job.progress_percentage = progress
                    job.processed_records = processed
                    job.high_confidence = high_confidence
                    job.medium_confidence = medium_confidence
                    job.low_confidence = low_confidence
                    job.failed_records = failed
                    
                    # Calculate job-level metrics
                    try:
                        MetricsCalculator.calculate_job_metrics(db, job_id)
                    except Exception as e:
                        logger.error(f"Error updating job metrics: {str(e)}")
                    
                    db.commit()
                    logger.info(f"Progress: {processed}/{total} ({progress:.1f}%)")
                
            except Exception as e:
                logger.error(f"Error processing entity: {str(e)}", exc_info=True)
                # Even with processing errors, give LOW confidence instead of FAILED
                entity.confidence_level = 'LOW' 
                entity.record_status = 'REVIEW'
                entity.overall_confidence_score = 20  # Minimum score
                entity.requires_manual_review = True
                low_confidence += 1
                processed += 1
        
        # Final update
        job.status = 'COMPLETED'
        job.completed_at = datetime.utcnow()
        job.progress_percentage = 100.0
        job.processed_records = processed
        job.high_confidence = high_confidence
        job.medium_confidence = medium_confidence
        job.low_confidence = low_confidence
        job.failed_records = failed
        job.osm_fields_filled_count = total_filled
        job.osm_fields_corrected_count = total_corrected
        
        # Calculate final job-level metrics
        try:
            job_metrics = MetricsCalculator.calculate_job_metrics(db, job_id)
            logger.info(f"Quality journey: {job_metrics.get('quality_journey', {})}")
        except Exception as e:
            logger.error(f"Error calculating final metrics: {str(e)}")
        
        db.commit()
        
        logger.info(f"╔══════════════════════════════════════════╗")
        logger.info(f"║ Validation Complete: {job_id[:8]}...       ║")
        logger.info(f"╠══════════════════════════════════════════╣")
        logger.info(f"║ Processed: {processed:4d}                      ║")
        logger.info(f"║ High:      {high_confidence:4d}                      ║")
        logger.info(f"║ Medium:    {medium_confidence:4d}                      ║")
        logger.info(f"║ Low:       {low_confidence:4d}                      ║")
        logger.info(f"║ Failed:    {failed:4d}                      ║")
        logger.info(f"║ Filled:    {total_filled:4d} fields               ║")
        logger.info(f"║ Corrected: {total_corrected:4d} fields               ║")
        logger.info(f"╚══════════════════════════════════════════╝")
        
        return {
            'status': 'completed',
            'processed': processed,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'failed': failed,
            'filled': total_filled,
            'corrected': total_corrected
        }
        
    except Exception as e:
        logger.error(f"Fatal error in validation task: {str(e)}", exc_info=True)
        if job:
            job.status = 'FAILED'
            job.completed_at = datetime.utcnow()
            db.commit()
        return {'status': 'failed', 'error': str(e)}
        
    finally:
        db.close()


def _calculate_confidence(entity, validation_result: dict) -> float:
    """
    Calculate confidence score based on:
    - Source-aware geocoding trust
    - Completeness
    - Fields filled
    - Fields corrected (lighter penalty for OpenAI)
    """
    score = 0.0

    # -------------------------
    # Geocoding / Source trust
    # -------------------------
    if entity.validation_source == 'BIFROST':
        # OpenAI does not provide lat/lng – do NOT penalize
        score += 30
    elif entity.has_geocoding:
        score += 30

    # -------------------------
    # Completeness (50 points)
    # -------------------------
    total_fields = 6
    complete_fields = sum([
        bool(entity.entity_name_osm),
        bool(entity.address1_osm),
        bool(entity.city_osm),
        bool(entity.state_osm),
        bool(entity.zip_osm),
        bool(entity.country_osm)
    ])
    score += (complete_fields / total_fields) * 50

    # -------------------------
    # Filled fields bonus
    # -------------------------
    score += len(validation_result.get('filled', [])) * 4

    # -------------------------
    # Corrected fields penalty
    # -------------------------
    if entity.validation_source == 'BIFROST':
        # OpenAI "corrections" are usually normalization, not bad data
        score -= len(validation_result.get('corrected', [])) * 1
    else:
        score -= len(validation_result.get('corrected', [])) * 5

    return max(0, min(100, score))

@celery_app.task(name='test_task')
def test_task():
    """Simple test task to verify Celery is working"""
    logger.info("Test task executed successfully!")
    return {'status': 'success', 'message': 'Celery is working!'}
