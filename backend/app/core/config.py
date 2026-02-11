"""
Application Configuration Settings
WITH AUTHENTICATION SETTINGS
"""
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Address Validation Platform"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # JWT Authentication (NEW)
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", 
        "your-super-secret-jwt-key-change-this-in-production-make-it-long-and-random"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres123@database:5432/address_validation"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://database:6379/0")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:80"
    ).split(",")
    
    # File Upload
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    UPLOAD_DIR: str = "/app/uploads"
    EXPORT_DIR: str = "/app/exports"
    ALLOWED_EXTENSIONS: List[str] = [".xlsx", ".xls", ".csv"]
    
    # Validators
    ENABLE_OSM_VALIDATOR: bool = os.getenv("ENABLE_OSM_VALIDATOR", "true").lower() == "true"
    ENABLE_USPS_API: bool = os.getenv("ENABLE_USPS_API", "false").lower() == "true"
    ENABLE_GOOGLE_VALIDATOR: bool = os.getenv("ENABLE_GOOGLE_VALIDATOR", "false").lower() == "true"
    ENABLE_CHATGPT_ENHANCEMENT: bool = os.getenv("ENABLE_CHATGPT_ENHANCEMENT", "false").lower() == "true"
    
    # API Keys
    USPS_API_KEY: str = os.getenv("USPS_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Rate Limiting
    OSM_RATE_LIMIT: float = float(os.getenv("OSM_RATE_LIMIT", "1.0"))  # requests per second
    
    # Validation Thresholds
    AUTO_APPROVE_THRESHOLD: float = float(os.getenv("AUTO_APPROVE_THRESHOLD", "90.0"))
    MANUAL_REVIEW_THRESHOLD: float = float(os.getenv("MANUAL_REVIEW_THRESHOLD", "70.0"))
    CHATGPT_ENHANCEMENT_THRESHOLD: float = float(os.getenv("CHATGPT_ENHANCEMENT_THRESHOLD", "90.0"))  # Enhance records below this
    
    # Celery
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    CELERY_WORKERS: int = int(os.getenv("CELERY_WORKERS", "4"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
