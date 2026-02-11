"""
Database Models - Validation Jobs and Entities
REFACTORED: Supplier → Entity (for Suppliers, Customers, Employees, etc.)
WITH AUTHENTICATION MODELS AND 3-STAGE VALIDATION
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from backend.app.core.database import Base


# ============================================
# AUTHENTICATION MODELS
# ============================================

class Role(Base):
    """User roles for access control"""
    __tablename__ = "roles"
    
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", back_populates="role")


class User(Base):
    """Application users with authentication"""
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(255))
    role_id = Column(Integer, ForeignKey('roles.role_id'), default=2)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assigned_validator = Column(String(100), nullable=True)
    
    # Relationships
    role = relationship("Role", back_populates="users")
    created_jobs = relationship("ValidationJob", back_populates="creator", foreign_keys="[ValidationJob.created_by]")
    created_validators = relationship("ValidatorConfig", back_populates="creator", foreign_keys="[ValidatorConfig.created_by]")



# ============================================
# VALIDATION MODELS
# ============================================

class ValidationJob(Base):
    __tablename__ = "validation_jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(255), nullable=False)
    client_name = Column(String(255))
    uploaded_file_name = Column(String(255))
    uploaded_file_path = Column(String(500))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Status tracking
    status = Column(String(50), default='UPLOADED')
    current_step = Column(String(100))
    progress_percentage = Column(DECIMAL(5,2), default=0.00)
    
    # Statistics
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    high_confidence = Column(Integer, default=0)
    medium_confidence = Column(Integer, default=0)
    low_confidence = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    
    # Settings
    settings = Column(JSONB)
    auto_approve_threshold = Column(DECIMAL(5,2), default=90.00)
    manual_review_threshold = Column(DECIMAL(5,2), default=70.00)
    
    # User info
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Metadata
    job_metadata = Column(JSONB)
    
    # Relationships (REFACTORED: suppliers → entities)
    entities = relationship("Entity", back_populates="job", cascade="all, delete-orphan")
    validation_history = relationship("ValidationHistory", back_populates="job")
    review_queue = relationship("ReviewQueue", back_populates="job")
    creator = relationship("User", back_populates="created_jobs", foreign_keys=[created_by])


class Entity(Base):
    """
    REFACTORED from Supplier
    Represents any entity: Supplier, Customer, Employee, etc.
    """
    __tablename__ = "entities"
    
    entity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('validation_jobs.job_id', ondelete='CASCADE'), nullable=False)
    row_number = Column(Integer)
    
    # ============================================
    # STAGE 1: ORIGINAL DATA
    # ============================================
    entity_name_original = Column(String(500))  # Was: vendor_original
    address1_original = Column(String(500))
    address2_original = Column(String(500))
    address3_original = Column(String(500))
    city_original = Column(String(255))
    state_original = Column(String(50))
    zip_original = Column(String(20))
    country_original = Column(String(50))
    
    # ============================================
    # STAGE 2: OSM FILLED & CORRECTED
    # ============================================
    entity_name_osm = Column(String(500))  # Was: vendor_osm
    address1_osm = Column(String(500))
    address2_osm = Column(String(500))
    city_osm = Column(String(255))
    state_osm = Column(String(50))
    zip_osm = Column(String(20))
    zip4_osm = Column(String(10))
    country_osm = Column(String(50))
    osm_source = Column(String(50))
    fields_filled_by_osm = Column(JSONB)
    fields_corrected_by_osm = Column(JSONB)
    osm_corrections = Column(JSONB)
    fill_percentage = Column(DECIMAL(5,2), default=0.00)
    correction_percentage = Column(DECIMAL(5,2), default=0.00)
    
    # ============================================
    # STAGE 3: ORACLE TRANSFORMED
    # ============================================
    entity_name_ora = Column(String(500))  # Was: vendor_ora
    address1_ora = Column(String(500))
    address2_ora = Column(String(500))
    address3_ora = Column(String(500))
    address4_ora = Column(String(500))
    city_ora = Column(String(255))
    state_ora = Column(String(50))
    zip_ora = Column(String(20))
    country_ora = Column(String(50))
    fill_stage = Column(String(20), default='original')
    
    # ============================================
    # LEGACY VALIDATED COLUMNS (for compatibility)
    # ============================================
    entity_name_validated = Column(String(500))  # Was: vendor_validated
    address1_validated = Column(String(500))
    address2_validated = Column(String(500))
    city_validated = Column(String(255))
    state_validated = Column(String(50))
    zip_validated = Column(String(20))
    zip4_validated = Column(String(10))
    county_validated = Column(String(100))
    country_validated = Column(String(50))
    
    # ============================================
    # USPS STANDARDIZED FORMAT
    # ============================================
    usps_delivery_line_1 = Column(String(500))
    usps_delivery_line_2 = Column(String(500))
    usps_last_line = Column(String(255))
    usps_formatted_full = Column(Text)
    
    # ============================================
    # ADDRESS COMPONENTS
    # ============================================
    address_components = Column(JSONB)
    address_parse_success = Column(Boolean, default=False)
    
    # ============================================
    # GEOCODING
    # ============================================
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    has_geocoding = Column(Boolean, default=False)
    
    # ============================================
    # ENTITY VALIDATION (was: VENDOR VALIDATION)
    # ============================================
    entity_name_from_address = Column(String(500))  # Was: vendor_name_from_address
    entity_match_score = Column(DECIMAL(5,2))       # Was: vendor_match_score
    entity_dba_name = Column(String(500))           # Was: vendor_dba_name
    
    # ============================================
    # CONFIDENCE & QUALITY
    # ============================================
    overall_confidence_score = Column(DECIMAL(5,2), default=0.00)
    confidence_level = Column(String(20))  # HIGH, MEDIUM, LOW, NONE
    record_status = Column(String(50), default='PENDING')  # READY, REVIEW, BLOCKED, MANUAL
    
    # ============================================
    # VALIDATION SOURCE TRACKING
    # ============================================
    validation_source = Column(String(100))
    validator_priority = Column(Integer)
    
    # ============================================
    # FLAGS
    # ============================================
    requires_manual_review = Column(Boolean, default=False)
    is_po_box = Column(Boolean, default=False)
    is_residential = Column(Boolean)
    is_valid_usps = Column(Boolean, default=False)
    
    # ============================================
    # METRICS - Original Completeness
    # ============================================
    missing_entity_name_original = Column(Boolean, default=False)  # Was: missing_vendor_original
    missing_address1_original = Column(Boolean, default=False)
    missing_city_original = Column(Boolean, default=False)
    missing_state_original = Column(Boolean, default=False)
    missing_zip_original = Column(Boolean, default=False)
    missing_country_original = Column(Boolean, default=False)
    
    # ============================================
    # METRICS - OSM Fill Tracking
    # ============================================
    osm_filled_entity_name = Column(Boolean, default=False)  # Was: osm_filled_vendor
    osm_filled_address1 = Column(Boolean, default=False)
    osm_filled_city = Column(Boolean, default=False)
    osm_filled_state = Column(Boolean, default=False)
    osm_filled_zip = Column(Boolean, default=False)
    osm_filled_country = Column(Boolean, default=False)
    
    # ============================================
    # METRICS - Oracle Transformation Tracking
    # ============================================
    trans_entity_name_uppercase = Column(Boolean, default=False)  # Was: trans_vendor_uppercase
    trans_state_to_code = Column(Boolean, default=False)
    trans_address_abbrev = Column(Boolean, default=False)
    trans_directional_fix = Column(Boolean, default=False)
    trans_zip_plus4 = Column(Boolean, default=False)
    
    # ============================================
    # METRICS - Completeness by Stage
    # ============================================
    completeness_original = Column(DECIMAL(5,2), default=0.0)
    completeness_osm = Column(DECIMAL(5,2), default=0.0)
    completeness_oracle = Column(DECIMAL(5,2), default=0.0)
    
    # ============================================
    # AUDIT TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))
    
    # ============================================
    # ADDITIONAL METADATA
    # ============================================
    validation_metadata = Column(JSONB)
    review_notes = Column(Text)
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    job = relationship("ValidationJob", back_populates="entities")
    validation_history = relationship("ValidationHistory", back_populates="entity")
    review_queue = relationship("ReviewQueue", back_populates="entity")


class ValidationHistory(Base):
    __tablename__ = "validation_history"
    
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey('entities.entity_id', ondelete='CASCADE'))
    job_id = Column(UUID(as_uuid=True), ForeignKey('validation_jobs.job_id', ondelete='CASCADE'))
    
    validation_step = Column(String(100))
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    change_reason = Column(Text)
    confidence_score = Column(DECIMAL(5,2))
    validation_source = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))
    
    history_metadata = Column(JSONB)
    
    # Relationships
    entity = relationship("Entity", back_populates="validation_history")
    job = relationship("ValidationJob", back_populates="validation_history")


class ReviewQueue(Base):
    __tablename__ = "review_queue"
    
    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey('entities.entity_id', ondelete='CASCADE'))
    job_id = Column(UUID(as_uuid=True), ForeignKey('validation_jobs.job_id', ondelete='CASCADE'))
    
    priority = Column(String(20), default='MEDIUM')
    issue_type = Column(String(100))
    issue_description = Column(Text)
    suggested_correction = Column(JSONB)
    
    status = Column(String(50), default='PENDING')
    assigned_to = Column(String(100))
    reviewed_by = Column(String(100))
    review_notes = Column(Text)
    resolution_action = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    entity = relationship("Entity", back_populates="review_queue")
    job = relationship("ValidationJob", back_populates="review_queue")


class ValidatorConfig(Base):
    __tablename__ = "validator_config"
    
    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validator_type = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, nullable=False)
    
    # API Configuration
    api_endpoint = Column(String(500))
    api_key_encrypted = Column(Text)
    
    # Rate limiting
    rate_limit = Column(Integer, default=1)
    timeout_seconds = Column(Integer, default=10)
    max_retries = Column(Integer, default=3)
    
    # Cost tracking
    cost_per_1000_requests = Column(DECIMAL(10,4), default=0.0)
    monthly_quota = Column(Integer)
    
    # Additional settings
    settings = Column(JSONB)
    
    # User tracking
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_validators", foreign_keys=[created_by])
