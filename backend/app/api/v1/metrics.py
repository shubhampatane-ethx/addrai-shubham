"""
Metrics API Endpoint
REFACTORED: Supplier → Entity
Provides job-level and entity-level metrics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ValidationJob, Entity
from backend.app.services.metrics_calculator import MetricsCalculator
from typing import Dict, Any, List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/job/{job_id}/metrics")
async def get_job_metrics(
    job_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive metrics for a validation job
    
    Returns:
        - Summary cards data (Original, OSM, Oracle)
        - Chart data (Pie, Bar, Line)
        - Field-by-field breakdown table
    """
    try:
        # Get job
        job = db.query(ValidationJob).filter(
            ValidationJob.job_id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get entities
        entities = db.query(Entity).filter(
            Entity.job_id == job_id
        ).all()
        
        if not entities:
            return {
                "job_id": job_id,
                "job_name": job.job_name,
                "total_records": 0,
                "message": "No records found"
            }
        
        total_records = len(entities)
        
        # ============================================
        # SUMMARY CARDS DATA
        # ============================================
        
        summary_cards = {
            "original": {
                "title": "Original Data",
                "completeness": round(job.quality_original or 0, 1),
                "subtitle": f"{sum(1 for e in entities if e.completeness_original == 100)} of {total_records} complete",
                "description": "Data quality before validation"
            },
            "osm": {
                "title": "OSM Validation",
                "completeness": round(job.quality_osm or 0, 1),
                "subtitle": f"+{job.osm_fields_filled_count} fields filled",
                "description": f"{job.osm_records_improved} records improved"
            },
            "oracle": {
                "title": "Oracle Ready",
                "completeness": round(job.quality_oracle or 0, 1),
                "subtitle": f"{job.oracle_records_transformed} records transformed",
                "description": f"{job.high_confidence} ready for import"
            }
        }
        
        # ============================================
        # PIE CHART DATA - Record Distribution
        # ============================================
        
        ready_count = sum(1 for e in entities if e.record_status == 'READY')
        review_count = sum(1 for e in entities if e.record_status == 'REVIEW')
        failed_count = sum(1 for e in entities if e.record_status == 'FAILED')
        
        pie_chart_data = {
            "title": "Record Status Distribution",
            "labels": ["Ready", "Review", "Failed"],
            "data": [ready_count, review_count, failed_count],
            "colors": ["#4caf50", "#ff9800", "#f44336"],
            "total": total_records
        }
        
        # ============================================
        # BAR CHART DATA - Field Completeness
        # ============================================
        
        bar_chart_data = {
            "title": "Field Completeness Comparison",
            "labels": ["Entity Name", "Address", "City", "State", "ZIP"],
            "datasets": [
                {
                    "label": "Original",
                    "data": [
                        job.original_completeness_entity_name or 0,
                        job.original_completeness_address1 or 0,
                        job.original_completeness_city or 0,
                        job.original_completeness_state or 0,
                        job.original_completeness_zip or 0
                    ],
                    "color": "#2196f3"
                },
                {
                    "label": "OSM",
                    "data": [
                        round(sum(1 for e in entities if not e.missing_entity_name_original or e.osm_filled_entity_name) / total_records * 100, 1),
                        round(sum(1 for e in entities if not e.missing_address1_original or e.osm_filled_address1) / total_records * 100, 1),
                        round(sum(1 for e in entities if not e.missing_city_original or e.osm_filled_city) / total_records * 100, 1),
                        round(sum(1 for e in entities if not e.missing_state_original or e.osm_filled_state) / total_records * 100, 1),
                        round(sum(1 for e in entities if not e.missing_zip_original or e.osm_filled_zip) / total_records * 100, 1),
                    ],
                    "color": "#4caf50"
                },
                {
                    "label": "Oracle",
                    "data": [100, 100, 100, 100, 100],  # Oracle is always 100%
                    "color": "#9c27b0"
                }
            ]
        }
        
        # ============================================
        # LINE CHART DATA - Quality Journey
        # ============================================
        
        line_chart_data = {
            "title": "Quality Journey Through Pipeline",
            "labels": ["Original", "OSM Validated", "Oracle Formatted"],
            "data": [
                round(job.quality_original or 0, 1),
                round(job.quality_osm or 0, 1),
                round(job.quality_oracle or 0, 1)
            ],
            "color": "#2196f3",
            "improvement": round((job.quality_oracle or 0) - (job.quality_original or 0), 1)
        }
        
        # ============================================
        # FIELD-BY-FIELD BREAKDOWN TABLE
        # ============================================
        
        field_breakdown = []
        
        # Entity Name field
        field_breakdown.append({
            "field": "Entity Name",
            "original": round(job.original_completeness_entity_name or 0, 1),
            "osm": round(sum(1 for e in entities if e.entity_name_validated) / total_records * 100, 1),
            "oracle": 100,
            "osm_filled": sum(1 for e in entities if e.osm_filled_entity_name),
            "transformations": [
                f"Uppercase: {job.oracle_uppercase_count}" if job.oracle_uppercase_count > 0 else None
            ]
        })
        
        # Address field
        field_breakdown.append({
            "field": "Address Line 1",
            "original": round(job.original_completeness_address1 or 0, 1),
            "osm": round(sum(1 for e in entities if e.address1_validated) / total_records * 100, 1),
            "oracle": 100,
            "osm_filled": sum(1 for e in entities if e.osm_filled_address1),
            "transformations": [
                f"Abbreviations: {job.oracle_abbrev_count}" if job.oracle_abbrev_count > 0 else None,
                f"Directional fixes: {job.oracle_directional_fix_count}" if job.oracle_directional_fix_count > 0 else None
            ]
        })
        
        # City field
        field_breakdown.append({
            "field": "City",
            "original": round(job.original_completeness_city or 0, 1),
            "osm": round(sum(1 for e in entities if e.city_validated) / total_records * 100, 1),
            "oracle": 100,
            "osm_filled": sum(1 for e in entities if e.osm_filled_city),
            "transformations": [
                "Uppercase" if job.oracle_uppercase_count > 0 else None
            ]
        })
        
        # State field
        field_breakdown.append({
            "field": "State",
            "original": round(job.original_completeness_state or 0, 1),
            "osm": round(sum(1 for e in entities if e.state_validated) / total_records * 100, 1),
            "oracle": 100,
            "osm_filled": sum(1 for e in entities if e.osm_filled_state),
            "transformations": [
                f"2-letter codes: {job.oracle_state_code_count}" if job.oracle_state_code_count > 0 else None
            ]
        })
        
        # ZIP field
        field_breakdown.append({
            "field": "ZIP Code",
            "original": round(job.original_completeness_zip or 0, 1),
            "osm": round(sum(1 for e in entities if e.zip_validated) / total_records * 100, 1),
            "oracle": 100,
            "osm_filled": sum(1 for e in entities if e.osm_filled_zip),
            "transformations": [
                f"ZIP+4 format: {job.oracle_zip_plus4_count}" if job.oracle_zip_plus4_count > 0 else None
            ]
        })
        
        # Clean up None values from transformations
        for field in field_breakdown:
            field['transformations'] = [t for t in field['transformations'] if t is not None]
        
        # ============================================
        # AGGREGATE STATS
        # ============================================
        
        aggregate_stats = {
            "total_records": total_records,
            "total_fields_processed": total_records * 6,  # 6 fields per record
            "osm_fields_filled": job.osm_fields_filled_count,
            "osm_records_improved": job.osm_records_improved,
            "oracle_total_transformations": (
                job.oracle_uppercase_count +
                job.oracle_state_code_count +
                job.oracle_abbrev_count +
                job.oracle_directional_fix_count +
                job.oracle_zip_plus4_count
            ),
            "geocoding_added": job.osm_geocoding_added,
            "quality_improvement": round((job.quality_oracle or 0) - (job.quality_original or 0), 1)
        }
        
        # ============================================
        # RETURN COMPLETE METRICS
        # ============================================
        
        return {
            "job_id": job_id,
            "job_name": job.job_name,
            "status": job.status,
            "total_records": total_records,
            
            # Cards
            "summary_cards": summary_cards,
            
            # Charts
            "pie_chart": pie_chart_data,
            "bar_chart": bar_chart_data,
            "line_chart": line_chart_data,
            
            # Table
            "field_breakdown": field_breakdown,
            
            # Stats
            "aggregate_stats": aggregate_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")
