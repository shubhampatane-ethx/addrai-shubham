"""
Metrics Calculator Service
REFACTORED: Supplier → Entity
Calculate and track data quality metrics throughout the validation pipeline
"""
from typing import Dict, List, Any, Optional
from backend.app.models.models import Entity, ValidationJob
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate metrics for validation jobs and entities"""
    
    # Define which fields we track
    TRACKED_FIELDS = ['entity_name', 'address1', 'city', 'state', 'zip', 'country']
    
    @staticmethod
    def is_field_empty(value: Optional[str]) -> bool:
        """Check if a field is empty or None"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == '':
            return True
        return False
    
    @staticmethod
    def calculate_completeness(data: Dict[str, Any], fields: List[str]) -> float:
        """
        Calculate completeness percentage for given fields
        
        Args:
            data: Dictionary with field values
            fields: List of field names to check
            
        Returns:
            Completeness percentage (0-100)
        """
        if not fields:
            return 0.0
        
        filled_count = sum(1 for field in fields if not MetricsCalculator.is_field_empty(data.get(field)))
        return round((filled_count / len(fields)) * 100, 2)
    
    @classmethod
    def analyze_original_data(cls, entity: Entity) -> Dict[str, Any]:
        """
        Analyze original data before any validation
        
        Returns:
            Dictionary with missing fields and completeness score
        """
        original_data = {
            'entity_name': entity.entity_name_original,
            'address1': entity.address1_original,
            'city': entity.city_original,
            'state': entity.state_original,
            'zip': entity.zip_original,
            'country': entity.country_original
        }
        
        # Track which fields are missing
        missing_fields = {
            field: cls.is_field_empty(original_data[field])
            for field in cls.TRACKED_FIELDS
        }
        
        # Calculate completeness
        completeness = cls.calculate_completeness(original_data, cls.TRACKED_FIELDS)
        
        return {
            'missing_fields': missing_fields,
            'completeness': completeness,
            'data': original_data
        }
    
    @classmethod
    def analyze_osm_contribution(cls, entity: Entity, original_analysis: Dict) -> Dict[str, Any]:
        """
        Analyze what OSM filled in
        
        Args:
            entity: Entity with validated data
            original_analysis: Results from analyze_original_data
            
        Returns:
            Dictionary with OSM contributions
        """
        validated_data = {
            'entity_name': entity.entity_name_validated,
            'address1': entity.address1_validated,
            'city': entity.city_validated,
            'state': entity.state_validated,
            'zip': entity.zip_validated,
            'country': entity.country_validated
        }
        
        # Check which fields OSM filled
        osm_filled = {}
        for field in cls.TRACKED_FIELDS:
            was_missing = original_analysis['missing_fields'][field]
            now_has_value = not cls.is_field_empty(validated_data[field])
            osm_filled[field] = was_missing and now_has_value
        
        # Calculate completeness after OSM
        completeness = cls.calculate_completeness(validated_data, cls.TRACKED_FIELDS)
        
        # Count fields filled
        fields_filled_count = sum(1 for filled in osm_filled.values() if filled)
        
        return {
            'osm_filled': osm_filled,
            'completeness': completeness,
            'fields_filled_count': fields_filled_count,
            'data': validated_data
        }
    
    @classmethod
    def analyze_oracle_transformations(cls, entity: Entity, osm_analysis: Dict) -> Dict[str, Any]:
        """
        Analyze Oracle transformations applied
        
        Args:
            entity: Entity with Oracle-formatted data
            osm_analysis: Results from analyze_osm_contribution
            
        Returns:
            Dictionary with transformation details
        """
        transformations = {}
        
        # Check entity name uppercase transformation
        if entity.entity_name_validated:
            original_entity_name = entity.entity_name_original or entity.entity_name_validated
            is_uppercase = entity.entity_name_validated == entity.entity_name_validated.upper()
            was_different = original_entity_name != entity.entity_name_validated
            transformations['entity_name_uppercase'] = is_uppercase and was_different
        else:
            transformations['entity_name_uppercase'] = False
        
        # Check state code transformation (full name → 2-letter)
        if entity.state_validated:
            is_two_letter = len(entity.state_validated) == 2
            original_state = entity.state_original or ''
            was_longer = len(original_state) > 2
            transformations['state_to_code'] = is_two_letter and was_longer
        else:
            transformations['state_to_code'] = False
        
        # Check address abbreviations (STREET→ST, AVENUE→AVE, etc.)
        if entity.address1_validated:
            abbrev_patterns = [' ST', ' AVE', ' BLVD', ' DR', ' RD', ' LN', ' CT', ' PL']
            has_abbrev = any(pattern in entity.address1_validated for pattern in abbrev_patterns)
            transformations['address_abbrev'] = has_abbrev
        else:
            transformations['address_abbrev'] = False
        
        # Check directional fixes (NSHORE→N SHORE)
        if entity.address1_validated:
            directional_patterns = [' N ', ' S ', ' E ', ' W ', ' NE ', ' NW ', ' SE ', ' SW ']
            has_directional_space = any(pattern in entity.address1_validated for pattern in directional_patterns)
            # Check if original had concatenated version
            original_addr = entity.address1_original or ''
            had_concatenated = any(concat in original_addr.upper() for concat in ['NSHORE', 'SSHORE', 'NMAIN', 'SMAIN'])
            transformations['directional_fix'] = has_directional_space and had_concatenated
        else:
            transformations['directional_fix'] = False
        
        # Check ZIP+4 format
        if entity.zip_validated:
            has_plus4 = '-' in entity.zip_validated and len(entity.zip_validated) == 10
            transformations['zip_plus4'] = has_plus4
        else:
            transformations['zip_plus4'] = False
        
        # Oracle data is always 100% complete after transformation
        oracle_data = {
            'entity_name': entity.entity_name_validated or entity.entity_name_original or 'UNKNOWN',
            'address1': entity.address1_validated or entity.address1_original or '',
            'city': entity.city_validated or entity.city_original or '',
            'state': entity.state_validated or entity.state_original or '',
            'zip': entity.zip_validated or entity.zip_original or '',
            'country': entity.country_validated or 'US'
        }
        
        completeness = cls.calculate_completeness(oracle_data, cls.TRACKED_FIELDS)
        
        return {
            'transformations': transformations,
            'completeness': completeness,
            'total_transformations': sum(1 for t in transformations.values() if t)
        }
    
    @classmethod
    def update_entity_metrics(cls, entity: Entity) -> None:
        """
        Update all metrics for an entity
        Calculates original, OSM, and Oracle metrics and stores them
        """
        # Analyze original data
        original = cls.analyze_original_data(entity)
        
        # Store original missing fields
        entity.missing_entity_name_original = original['missing_fields']['entity_name']
        entity.missing_address1_original = original['missing_fields']['address1']
        entity.missing_city_original = original['missing_fields']['city']
        entity.missing_state_original = original['missing_fields']['state']
        entity.missing_zip_original = original['missing_fields']['zip']
        entity.missing_country_original = original['missing_fields']['country']
        entity.completeness_original = original['completeness']
        
        # Analyze OSM contribution
        osm = cls.analyze_osm_contribution(entity, original)
        
        # Store OSM filled fields
        entity.osm_filled_entity_name = osm['osm_filled']['entity_name']
        entity.osm_filled_address1 = osm['osm_filled']['address1']
        entity.osm_filled_city = osm['osm_filled']['city']
        entity.osm_filled_state = osm['osm_filled']['state']
        entity.osm_filled_zip = osm['osm_filled']['zip']
        entity.osm_filled_country = osm['osm_filled']['country']
        entity.completeness_osm = osm['completeness']
        
        # Analyze Oracle transformations
        oracle = cls.analyze_oracle_transformations(entity, osm)
        
        # Store transformations
        entity.trans_entity_name_uppercase = oracle['transformations']['entity_name_uppercase']
        entity.trans_state_to_code = oracle['transformations']['state_to_code']
        entity.trans_address_abbrev = oracle['transformations']['address_abbrev']
        entity.trans_directional_fix = oracle['transformations']['directional_fix']
        entity.trans_zip_plus4 = oracle['transformations']['zip_plus4']
        entity.completeness_oracle = oracle['completeness']
    
    @classmethod
    def calculate_job_metrics(cls, db: Session, job_id: str) -> Dict[str, Any]:
        """
        Calculate aggregate metrics for entire job
        
        Args:
            db: Database session
            job_id: Job ID
            
        Returns:
            Dictionary with job-level metrics
        """
        from sqlalchemy import func
        
        # Get job
        job = db.query(ValidationJob).filter(ValidationJob.job_id == job_id).first()
        if not job:
            return {}
        
        # Get all entities for this job
        entities = db.query(Entity).filter(Entity.job_id == job_id).all()
        
        if not entities:
            return {}
        
        total_records = len(entities)
        
        # Calculate original completeness by field
        original_completeness = {
            'entity_name': round(sum(1 for e in entities if not e.missing_entity_name_original) / total_records * 100, 2),
            'address1': round(sum(1 for e in entities if not e.missing_address1_original) / total_records * 100, 2),
            'city': round(sum(1 for e in entities if not e.missing_city_original) / total_records * 100, 2),
            'state': round(sum(1 for e in entities if not e.missing_state_original) / total_records * 100, 2),
            'zip': round(sum(1 for e in entities if not e.missing_zip_original) / total_records * 100, 2),
        }
        
        # Overall original completeness (average of all entities)
        avg_original = round(sum(e.completeness_original for e in entities) / total_records, 2)
        
        # OSM contribution
        osm_fields_filled = sum(
            sum([
                e.osm_filled_entity_name,
                e.osm_filled_address1,
                e.osm_filled_city,
                e.osm_filled_state,
                e.osm_filled_zip,
                e.osm_filled_country
            ])
            for e in entities
        )
        
        osm_records_improved = sum(1 for e in entities if e.completeness_osm > e.completeness_original)
        osm_success_rate = round((job.high_confidence + job.medium_confidence) / total_records * 100, 2) if total_records > 0 else 0
        osm_geocoding_added = sum(1 for e in entities if e.has_geocoding)
        
        # Oracle transformations
        oracle_uppercase = sum(1 for e in entities if e.trans_entity_name_uppercase)
        oracle_state_codes = sum(1 for e in entities if e.trans_state_to_code)
        oracle_abbrev = sum(1 for e in entities if e.trans_address_abbrev)
        oracle_directional = sum(1 for e in entities if e.trans_directional_fix)
        oracle_zip_plus4 = sum(1 for e in entities if e.trans_zip_plus4)
        
        # Quality journey
        avg_osm = round(sum(e.completeness_osm for e in entities) / total_records, 2)
        avg_oracle = round(sum(e.completeness_oracle for e in entities) / total_records, 2)
        
        # Update job with metrics
        job.original_completeness_overall = avg_original
        job.original_completeness_entity_name = original_completeness['entity_name']
        job.original_completeness_address1 = original_completeness['address1']
        job.original_completeness_city = original_completeness['city']
        job.original_completeness_state = original_completeness['state']
        job.original_completeness_zip = original_completeness['zip']
        
        job.osm_fields_filled_count = osm_fields_filled
        job.osm_records_improved = osm_records_improved
        job.osm_success_rate = osm_success_rate
        job.osm_geocoding_added = osm_geocoding_added
        
        job.oracle_records_transformed = total_records
        job.oracle_uppercase_count = oracle_uppercase
        job.oracle_state_code_count = oracle_state_codes
        job.oracle_abbrev_count = oracle_abbrev
        job.oracle_directional_fix_count = oracle_directional
        job.oracle_zip_plus4_count = oracle_zip_plus4
        
        job.quality_original = avg_original
        job.quality_osm = avg_osm
        job.quality_oracle = avg_oracle
        
        db.commit()
        
        return {
            'total_records': total_records,
            'original_completeness': original_completeness,
            'original_completeness_overall': avg_original,
            'osm_contribution': {
                'fields_filled': osm_fields_filled,
                'records_improved': osm_records_improved,
                'success_rate': osm_success_rate,
                'geocoding_added': osm_geocoding_added
            },
            'oracle_transformation': {
                'records_transformed': total_records,
                'uppercase_count': oracle_uppercase,
                'state_code_count': oracle_state_codes,
                'abbrev_count': oracle_abbrev,
                'directional_fix_count': oracle_directional,
                'zip_plus4_count': oracle_zip_plus4
            },
            'quality_journey': {
                'original': avg_original,
                'osm': avg_osm,
                'oracle': avg_oracle
            }
        }
