"""
CSV Export Service - Oracle Fusion Compatible Format
REFACTORED: Supplier → Entity
Exports validated addresses in Oracle Fusion import format
"""
import pandas as pd
import os
from typing import List
from datetime import datetime
from backend.app.models.models import Entity, ValidationJob
from backend.app.core.config import settings

class OracleFusionExporter:
    """
    Export validated entity addresses to Oracle Fusion CSV format
    
    Oracle Fusion Import Standard Columns:
    - Entity Name (Supplier/Customer/Employee/etc.)
    - Address Name
    - Address Line 1
    - Address Line 2  
    - Address Line 3
    - City
    - State
    - Postal Code
    - Country
    - County (Optional)
    
    Additional Quality Columns:
    - Validation Status
    - Confidence Level
    - Latitude
    - Longitude
    """
    
    def __init__(self):
        self.export_dir = settings.EXPORT_DIR
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_job_to_csv(
        self, 
        job: ValidationJob, 
        entities: List[Entity],
        include_metadata: bool = False
    ) -> str:
        """
        Export entities to Oracle Fusion CSV format
        
        Args:
            job: ValidationJob object
            entities: List of Entity objects
            include_metadata: Include validation metadata columns
        
        Returns:
            Path to exported CSV file
        """
        # Build data rows
        data = []
        
        for entity in entities:
            row = self._build_oracle_row(entity, include_metadata)
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Oracle_Fusion_Entities_{job.job_name}_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)
        
        # Export to CSV
        df.to_csv(filepath, index=False, encoding='utf-8-sig')  # UTF-8 with BOM for Excel
        
        return filepath
    
    def _build_oracle_row(self, entity: Entity, include_metadata: bool) -> dict:
        """
        Build single row for Oracle Fusion import
        """
        # Determine which address to use (validated if available, original if not)
        use_validated = (
            entity.validated_at is not None and 
            entity.record_status == 'READY'
        )
        
        # Standard Oracle Fusion columns
        row = {
            'Entity Name': entity.entity_name_validated if use_validated else entity.entity_name_original,
            'Address Name': f"{entity.entity_name_original or 'Unknown'} - Main Address",
            'Address Line 1': entity.usps_delivery_line_1 or entity.address1_validated or entity.address1_original,
            'Address Line 2': entity.usps_delivery_line_2 or entity.address2_validated or entity.address2_original,
            'Address Line 3': '',  # Oracle Fusion optional line
            'City': entity.city_validated or entity.city_original,
            'State': entity.state_validated or entity.state_original,
            'Postal Code': entity.zip_validated or entity.zip_original,
            'Country': entity.country_validated or entity.country_original or 'US',
        }
        
        # Add County if available
        if entity.county_validated:
            row['County'] = entity.county_validated
        
        # Add metadata columns if requested
        if include_metadata:
            row.update({
                'Validation Status': entity.record_status,
                'Confidence Level': entity.confidence_level,
                'Confidence Score': float(entity.overall_confidence_score) if entity.overall_confidence_score else 0.0,
                'Validation Source': entity.validation_source,
                'Latitude': float(entity.latitude) if entity.latitude else '',
                'Longitude': float(entity.longitude) if entity.longitude else '',
                'USPS Formatted': entity.usps_formatted_full or '',
                'Entity Match Score': float(entity.entity_match_score) if entity.entity_match_score else '',
                'Requires Review': 'YES' if entity.requires_manual_review else 'NO',
                'Geocoded': 'YES' if entity.has_geocoding else 'NO',
                'PO Box': 'YES' if entity.is_po_box else 'NO',
                'Validated Date': entity.validated_at.strftime('%Y-%m-%d') if entity.validated_at else ''
            })
        
        return row
    
    def export_high_confidence_only(
        self,
        job: ValidationJob,
        entities: List[Entity],
        min_confidence: float = 90.0
    ) -> str:
        """
        Export only high-confidence records ready for Oracle Fusion import
        """
        # Filter high-confidence records
        high_confidence_entities = [
            e for e in entities
            if e.confidence_level == 'HIGH' and 
               float(e.overall_confidence_score or 0) >= min_confidence and
               e.record_status == 'READY'
        ]
        
        if not high_confidence_entities:
            raise ValueError("No high-confidence records found to export")
        
        # Export without metadata (clean Oracle import)
        return self.export_job_to_csv(job, high_confidence_entities, include_metadata=False)
    
    def export_for_review(
        self,
        job: ValidationJob,
        entities: List[Entity]
    ) -> str:
        """
        Export records that need manual review with full metadata
        """
        # Filter records needing review
        review_entities = [
            e for e in entities
            if e.requires_manual_review or 
               e.record_status in ['REVIEW', 'BLOCKED'] or
               e.confidence_level in ['LOW', 'MEDIUM']
        ]
        
        if not review_entities:
            raise ValueError("No records needing review found")
        
        # Export WITH metadata for review
        return self.export_job_to_csv(job, review_entities, include_metadata=True)
    
    def export_comparison_report(
        self,
        job: ValidationJob,
        entities: List[Entity]
    ) -> str:
        """
        Export before/after comparison report
        """
        data = []
        
        for entity in entities:
            row = {
                # Original Data
                'Original Entity Name': entity.entity_name_original,
                'Original Address1': entity.address1_original,
                'Original Address2': entity.address2_original,
                'Original City': entity.city_original,
                'Original State': entity.state_original,
                'Original ZIP': entity.zip_original,
                
                # Validated Data
                'Validated Entity Name': entity.entity_name_validated,
                'Validated Address1': entity.address1_validated,
                'Validated City': entity.city_validated,
                'Validated State': entity.state_validated,
                'Validated ZIP': entity.zip_validated,
                
                # USPS Formatted
                'USPS Address Line 1': entity.usps_delivery_line_1,
                'USPS Last Line': entity.usps_last_line,
                
                # Quality Metrics
                'Confidence Score': float(entity.overall_confidence_score) if entity.overall_confidence_score else 0.0,
                'Confidence Level': entity.confidence_level,
                'Status': entity.record_status,
                'Validation Source': entity.validation_source,
                
                # Geocoding
                'Latitude': float(entity.latitude) if entity.latitude else '',
                'Longitude': float(entity.longitude) if entity.longitude else '',
                
                # Changes
                'Address Changed': 'YES' if entity.address1_validated != entity.address1_original else 'NO',
                'City Changed': 'YES' if entity.city_validated != entity.city_original else 'NO',
                'State Changed': 'YES' if entity.state_validated != entity.state_original else 'NO',
                'ZIP Changed': 'YES' if entity.zip_validated != entity.zip_original else 'NO'
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Comparison_Report_{job.job_name}_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        return filepath
    
    def generate_summary_report(self, job: ValidationJob, entities: List[Entity]) -> dict:
        """
        Generate summary statistics for the job
        """
        total = len(entities)
        
        # Count by confidence level
        high_conf = sum(1 for e in entities if e.confidence_level == 'HIGH')
        medium_conf = sum(1 for e in entities if e.confidence_level == 'MEDIUM')
        low_conf = sum(1 for e in entities if e.confidence_level == 'LOW')
        none_conf = sum(1 for e in entities if e.confidence_level == 'NONE')
        
        # Count by status
        ready = sum(1 for e in entities if e.record_status == 'READY')
        review = sum(1 for e in entities if e.record_status == 'REVIEW')
        blocked = sum(1 for e in entities if e.record_status == 'BLOCKED')
        
        # Calculate average confidence
        avg_confidence = sum(
            float(e.overall_confidence_score or 0) for e in entities
        ) / total if total > 0 else 0
        
        # Count geocoded
        geocoded = sum(1 for e in entities if e.has_geocoding)
        
        # Count by validation source
        osm_count = sum(1 for e in entities if e.validation_source and 'OSM' in e.validation_source)
        chatgpt_count = sum(1 for e in entities if e.validation_source and 'ChatGPT' in e.validation_source)
        
        return {
            'job_name': job.job_name,
            'total_records': total,
            'confidence_breakdown': {
                'HIGH': high_conf,
                'MEDIUM': medium_conf,
                'LOW': low_conf,
                'NONE': none_conf
            },
            'status_breakdown': {
                'READY': ready,
                'REVIEW': review,
                'BLOCKED': blocked
            },
            'quality_metrics': {
                'average_confidence': round(avg_confidence, 2),
                'geocoded_count': geocoded,
                'geocoded_percentage': round(geocoded / total * 100, 2) if total > 0 else 0
            },
            'validation_sources': {
                'OSM_Nominatim': osm_count,
                'ChatGPT_Enhanced': chatgpt_count
            },
            'oracle_fusion_ready': ready,
            'needs_review': review + blocked
        }
