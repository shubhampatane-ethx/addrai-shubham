--
-- AddrAI Database Initialization Script - ENTITY-BASED
-- Generated: 2025-12-23
-- ADMIN USER: Created automatically by create-admin-user.py script
-- COMPLETE SCHEMA - ALL 80+ COLUMNS from models.py
-- REFACTORED: Supplier → Entity (for Suppliers, Customers, Employees, etc.)
--

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Drop existing tables (clean slate)
DROP TABLE IF EXISTS api_usage_log CASCADE;
DROP TABLE IF EXISTS review_queue CASCADE;
DROP TABLE IF EXISTS validation_history CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS validation_jobs CASCADE;
DROP TABLE IF EXISTS validator_config CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- ========================================
-- ROLES TABLE
-- ========================================
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO roles (role_id, role_name, description) VALUES
(1, 'admin', 'Administrator with full access'),
(2, 'user', 'Regular user with limited access');

-- ========================================
-- USERS TABLE
-- ========================================
CREATE TABLE users (
    user_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role_id INTEGER DEFAULT 2 REFERENCES roles(role_id),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- NOTE: Admin user is created by /app/backend/create-admin-user.py script
-- This ensures bcrypt compatibility between Python and PostgreSQL

-- ========================================
-- VALIDATOR_CONFIG TABLE
-- ========================================
CREATE TABLE validator_config (
    config_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    validator_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER NOT NULL,
    
    -- API Configuration
    api_endpoint VARCHAR(500),
    api_key_encrypted TEXT,
    
    -- Rate limiting
    rate_limit INTEGER DEFAULT 1,
    timeout_seconds INTEGER DEFAULT 10,
    max_retries INTEGER DEFAULT 3,
    
    -- Cost tracking
    cost_per_1000_requests NUMERIC(10,4) DEFAULT 0.0,
    monthly_quota INTEGER,
    
    -- Additional settings
    settings JSONB,
    
    -- User tracking
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default validators
INSERT INTO validator_config (validator_type, display_name, enabled, priority, cost_per_1000_requests)
VALUES 
    ('osm_nominatim', 'OpenStreetMap Nominatim', true, 1, 0),
    ('google_maps', 'Google Maps Geocoding', false, 2, 5.00),
    ('mapbox', 'Mapbox Geocoding', false, 3, 4.00);

-- ========================================
-- VALIDATION_JOBS TABLE
-- ========================================
CREATE TABLE validation_jobs (
    job_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    uploaded_file_name VARCHAR(255),
    uploaded_file_path VARCHAR(500),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'UPLOADED',
    current_step VARCHAR(100),
    progress_percentage NUMERIC(5,2) DEFAULT 0.00,
    
    -- Statistics
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    high_confidence INTEGER DEFAULT 0,
    medium_confidence INTEGER DEFAULT 0,
    low_confidence INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    
    -- Settings
    settings JSONB,
    auto_approve_threshold NUMERIC(5,2) DEFAULT 90.00,
    manual_review_threshold NUMERIC(5,2) DEFAULT 70.00,
    
    -- User info
    created_by UUID REFERENCES users(user_id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Metadata
    job_metadata JSONB
);

-- ========================================
-- ENTITIES TABLE (was: SUPPLIERS)
-- COMPLETE SCHEMA - ALL 80+ COLUMNS
-- ========================================
CREATE TABLE entities (
    -- Primary Key
    entity_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    job_id UUID REFERENCES validation_jobs(job_id) ON DELETE CASCADE NOT NULL,
    row_number INTEGER,
    
    -- STAGE 1: ORIGINAL DATA
    entity_name_original VARCHAR(500),
    address1_original VARCHAR(500),
    address2_original VARCHAR(500),
    address3_original VARCHAR(500),
    city_original VARCHAR(255),
    state_original VARCHAR(50),
    zip_original VARCHAR(20),
    country_original VARCHAR(50),
    
    -- STAGE 2: OSM FILLED & CORRECTED
    entity_name_osm VARCHAR(500),
    address1_osm VARCHAR(500),
    address2_osm VARCHAR(500),
    city_osm VARCHAR(255),
    state_osm VARCHAR(50),
    zip_osm VARCHAR(20),
    zip4_osm VARCHAR(10),
    country_osm VARCHAR(50),
    osm_source VARCHAR(50),
    fields_filled_by_osm JSONB,
    fields_corrected_by_osm JSONB,
    osm_corrections JSONB,
    fill_percentage NUMERIC(5,2) DEFAULT 0.00,
    correction_percentage NUMERIC(5,2) DEFAULT 0.00,
    
    -- STAGE 3: ORACLE TRANSFORMED
    entity_name_ora VARCHAR(500),
    address1_ora VARCHAR(500),
    address2_ora VARCHAR(500),
    address3_ora VARCHAR(500),
    address4_ora VARCHAR(500),
    city_ora VARCHAR(255),
    state_ora VARCHAR(50),
    zip_ora VARCHAR(20),
    country_ora VARCHAR(50),
    fill_stage VARCHAR(20) DEFAULT 'original',
    
    -- LEGACY VALIDATED COLUMNS
    entity_name_validated VARCHAR(500),
    address1_validated VARCHAR(500),
    address2_validated VARCHAR(500),
    city_validated VARCHAR(255),
    state_validated VARCHAR(50),
    zip_validated VARCHAR(20),
    zip4_validated VARCHAR(10),
    county_validated VARCHAR(100),
    country_validated VARCHAR(50),
    
    -- USPS STANDARDIZED FORMAT
    usps_delivery_line_1 VARCHAR(500),
    usps_delivery_line_2 VARCHAR(500),
    usps_last_line VARCHAR(255),
    usps_formatted_full TEXT,
    
    -- ADDRESS COMPONENTS
    address_components JSONB,
    address_parse_success BOOLEAN DEFAULT false,
    
    -- GEOCODING
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    has_geocoding BOOLEAN DEFAULT false,
    
    -- ENTITY VALIDATION
    entity_name_from_address VARCHAR(500),
    entity_match_score NUMERIC(5,2),
    entity_dba_name VARCHAR(500),
    
    -- CONFIDENCE & QUALITY
    overall_confidence_score NUMERIC(5,2) DEFAULT 0.00,
    confidence_level VARCHAR(20),
    record_status VARCHAR(50) DEFAULT 'PENDING',
    
    -- VALIDATION SOURCE TRACKING
    validation_source VARCHAR(100),
    validator_priority INTEGER,
    
    -- FLAGS
    requires_manual_review BOOLEAN DEFAULT false,
    is_po_box BOOLEAN DEFAULT false,
    is_residential BOOLEAN,
    is_valid_usps BOOLEAN DEFAULT false,
    
    -- METRICS - Original Completeness
    missing_entity_name_original BOOLEAN DEFAULT false,
    missing_address1_original BOOLEAN DEFAULT false,
    missing_city_original BOOLEAN DEFAULT false,
    missing_state_original BOOLEAN DEFAULT false,
    missing_zip_original BOOLEAN DEFAULT false,
    missing_country_original BOOLEAN DEFAULT false,
    
    -- METRICS - OSM Fill Tracking
    osm_filled_entity_name BOOLEAN DEFAULT false,
    osm_filled_address1 BOOLEAN DEFAULT false,
    osm_filled_city BOOLEAN DEFAULT false,
    osm_filled_state BOOLEAN DEFAULT false,
    osm_filled_zip BOOLEAN DEFAULT false,
    osm_filled_country BOOLEAN DEFAULT false,
    
    -- METRICS - Oracle Transformation Tracking
    trans_entity_name_uppercase BOOLEAN DEFAULT false,
    trans_state_to_code BOOLEAN DEFAULT false,
    trans_address_abbrev BOOLEAN DEFAULT false,
    trans_directional_fix BOOLEAN DEFAULT false,
    trans_zip_plus4 BOOLEAN DEFAULT false,
    
    -- METRICS - Completeness by Stage
    completeness_original NUMERIC(5,2) DEFAULT 0.0,
    completeness_osm NUMERIC(5,2) DEFAULT 0.0,
    completeness_oracle NUMERIC(5,2) DEFAULT 0.0,
    
    -- AUDIT TIMESTAMPS
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100),
    
    -- ADDITIONAL METADATA
    validation_metadata JSONB,
    review_notes TEXT
);

-- ========================================
-- VALIDATION_HISTORY TABLE
-- ========================================
CREATE TABLE validation_history (
    history_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    entity_id UUID REFERENCES entities(entity_id) ON DELETE CASCADE,
    job_id UUID REFERENCES validation_jobs(job_id) ON DELETE CASCADE,
    
    validation_step VARCHAR(100),
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,
    confidence_score NUMERIC(5,2),
    validation_source VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    history_metadata JSONB
);

-- ========================================
-- REVIEW_QUEUE TABLE
-- ========================================
CREATE TABLE review_queue (
    review_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    entity_id UUID REFERENCES entities(entity_id) ON DELETE CASCADE,
    job_id UUID REFERENCES validation_jobs(job_id) ON DELETE CASCADE,
    
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    issue_type VARCHAR(100),
    issue_description TEXT,
    suggested_correction JSONB,
    
    status VARCHAR(50) DEFAULT 'PENDING',
    assigned_to VARCHAR(100),
    reviewed_by VARCHAR(100),
    review_notes TEXT,
    resolution_action VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    assigned_at TIMESTAMP,
    resolved_at TIMESTAMP
);

-- ========================================
-- API_USAGE_LOG TABLE
-- ========================================
CREATE TABLE api_usage_log (
    log_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    validator_type VARCHAR(100),
    job_id UUID REFERENCES validation_jobs(job_id) ON DELETE SET NULL,
    entity_id UUID REFERENCES entities(entity_id) ON DELETE SET NULL,
    request_url TEXT,
    request_payload JSONB,
    response_status INTEGER,
    response_data JSONB,
    response_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================
CREATE INDEX idx_entities_job_id ON entities(job_id);
CREATE INDEX idx_entities_confidence ON entities(confidence_level);
CREATE INDEX idx_entities_status ON entities(record_status);
CREATE INDEX idx_entities_row_number ON entities(job_id, row_number);
CREATE INDEX idx_validation_jobs_status ON validation_jobs(status);
CREATE INDEX idx_validation_jobs_created_at ON validation_jobs(created_at DESC);
CREATE INDEX idx_validation_history_entity ON validation_history(entity_id);
CREATE INDEX idx_validation_history_job ON validation_history(job_id);
CREATE INDEX idx_review_queue_entity ON review_queue(entity_id);
CREATE INDEX idx_review_queue_status ON review_queue(status);

-- ========================================
-- GRANTS
-- ========================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ========================================
-- SUCCESS MESSAGE
-- ========================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '  AddrAI Database - ENTITY-BASED SCHEMA';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema: COMPLETE with ALL 80+ columns';
    RAISE NOTICE 'Refactored: Supplier → Entity';
    RAISE NOTICE '  - suppliers table → entities table';
    RAISE NOTICE '  - supplier_id → entity_id';
    RAISE NOTICE '  - vendor_* → entity_name_*';
    RAISE NOTICE '';
    RAISE NOTICE 'Admin User: Created by startup script';
    RAISE NOTICE 'Login: admin / admin';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for: Suppliers, Customers, Employees';
    RAISE NOTICE '===========================================';
END $$;
