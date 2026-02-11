"""
Admin Configuration API Endpoints
Manage validator API keys, thresholds, and system settings
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.core.database import get_db
from backend.app.models.models import ValidatorConfig
from backend.app.services.chatgpt_validator import ChatGPTAddressValidator
from backend.app.services.osm_validator import OSMNominatimValidator
from backend.app.api.v1.roles import router as roles_router
import uuid

router = APIRouter()

class ValidatorConfigRequest(BaseModel):
    validator_type: str
    enabled: bool
    api_key: Optional[str] = None
    rate_limit: Optional[int] = None
    priority: Optional[int] = None
    settings: Optional[dict] = None

class ThresholdConfigRequest(BaseModel):
    auto_approve_threshold: float
    manual_review_threshold: float
    enable_chatgpt_enhancement: bool
    chatgpt_enhancement_threshold: float  # Only enhance records below this

@router.get("/validators")
async def list_validators(db: Session = Depends(get_db)):
    """
    Get all validator configurations
    """
    configs = db.query(ValidatorConfig).order_by(ValidatorConfig.priority).all()
    
    return {
        "validators": [
            {
                "config_id": str(c.config_id),
                "validator_type": c.validator_type,
                "enabled": c.enabled,
                "priority": c.priority,
                "has_api_key": bool(c.api_key_encrypted),
                "rate_limit": c.rate_limit,
                "cost_per_1000": float(c.cost_per_1000_requests) if c.cost_per_1000_requests else 0.0,
                "settings": c.settings
            }
            for c in configs
        ]
    }

@router.post("/validators")
async def create_or_update_validator(
    request: ValidatorConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Create or update validator configuration
    """
    # Check if validator config exists
    existing = db.query(ValidatorConfig).filter(
        ValidatorConfig.validator_type == request.validator_type
    ).first()
    
    if existing:
        # Update existing
        existing.enabled = request.enabled
        if request.api_key:
            existing.api_key_encrypted = request.api_key  # TODO: Encrypt in production
        if request.rate_limit is not None:
            existing.rate_limit = request.rate_limit
        if request.priority is not None:
            existing.priority = request.priority
        if request.settings:
            existing.settings = request.settings
        
        db.commit()
        db.refresh(existing)
        
        return {
            "message": "Validator configuration updated",
            "config_id": str(existing.config_id),
            "validator_type": existing.validator_type
        }
    else:
        # Create new
        new_config = ValidatorConfig(
            validator_type=request.validator_type,
            enabled=request.enabled,
            api_key_encrypted=request.api_key if request.api_key else None,
            rate_limit=request.rate_limit or 1,
            priority=request.priority or 99,
            settings=request.settings or {}
        )
        
        # Set cost based on validator type
        if request.validator_type == "chatgpt_gpt4":
            new_config.cost_per_1000_requests = 2.40  # ~$0.024 per address (400 tokens)
        elif request.validator_type == "google_geocoding":
            new_config.cost_per_1000_requests = 5.00
        else:
            new_config.cost_per_1000_requests = 0.0
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        return {
            "message": "Validator configuration created",
            "config_id": str(new_config.config_id),
            "validator_type": new_config.validator_type
        }

@router.put("/validators/{validator_type}/toggle")
async def toggle_validator(
    validator_type: str,
    enabled: bool,
    db: Session = Depends(get_db)
):
    """
    Quick toggle validator on/off
    """
    config = db.query(ValidatorConfig).filter(
        ValidatorConfig.validator_type == validator_type
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Validator not found")
    
    config.enabled = enabled
    db.commit()
    
    return {
        "message": f"Validator {'enabled' if enabled else 'disabled'}",
        "validator_type": validator_type,
        "enabled": enabled
    }

@router.post("/validators/test")
async def test_validator_connection(
    validator_type: str,
    api_key: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Test validator connection and API key
    """
    # Get config or use provided API key
    if not api_key:
        config = db.query(ValidatorConfig).filter(
            ValidatorConfig.validator_type == validator_type
        ).first()
        if not config or not config.api_key_encrypted:
            raise HTTPException(
                status_code=400,
                detail="No API key configured for this validator"
            )
        api_key = config.api_key_encrypted
    
    # Test based on validator type
    if validator_type == "chatgpt_gpt4" or validator_type == "openai":
        validator = ChatGPTAddressValidator(api_key=api_key)
        is_healthy = validator.health_check()
        
        return {
            "validator_type": validator_type,
            "status": "healthy" if is_healthy else "unreachable",
            "message": "API key is valid" if is_healthy else "API key is invalid or service unreachable"
        }
    
    elif validator_type == "osm_nominatim":
        validator = OSMNominatimValidator()
        is_healthy = validator.health_check()
        
        return {
            "validator_type": validator_type,
            "status": "healthy" if is_healthy else "unreachable",
            "message": "Service is accessible" if is_healthy else "Service is unreachable"
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown validator type: {validator_type}"
        )

@router.get("/thresholds")
async def get_thresholds():
    """
    Get current validation thresholds
    """
    from backend.app.core.config import settings
    
    return {
        "auto_approve_threshold": settings.AUTO_APPROVE_THRESHOLD,
        "manual_review_threshold": settings.MANUAL_REVIEW_THRESHOLD,
        "enable_chatgpt_enhancement": settings.ENABLE_CHATGPT_ENHANCEMENT,
        "chatgpt_enhancement_threshold": settings.CHATGPT_ENHANCEMENT_THRESHOLD
    }

@router.put("/thresholds")
async def update_thresholds(request: ThresholdConfigRequest):
    """
    Update validation thresholds
    
    Note: This updates runtime config, but doesn't persist to .env file
    For production, use environment variables or database storage
    """
    from backend.app.core.config import settings
    
    # Validate thresholds
    if request.auto_approve_threshold <= request.manual_review_threshold:
        raise HTTPException(
            status_code=400,
            detail="Auto-approve threshold must be higher than manual review threshold"
        )
    
    if request.chatgpt_enhancement_threshold > request.auto_approve_threshold:
        raise HTTPException(
            status_code=400,
            detail="ChatGPT enhancement threshold should be lower than auto-approve threshold"
        )
    
    # Update settings (runtime only)
    settings.AUTO_APPROVE_THRESHOLD = request.auto_approve_threshold
    settings.MANUAL_REVIEW_THRESHOLD = request.manual_review_threshold
    settings.ENABLE_CHATGPT_ENHANCEMENT = request.enable_chatgpt_enhancement
    settings.CHATGPT_ENHANCEMENT_THRESHOLD = request.chatgpt_enhancement_threshold
    
    return {
        "message": "Thresholds updated successfully",
        "thresholds": {
            "auto_approve_threshold": settings.AUTO_APPROVE_THRESHOLD,
            "manual_review_threshold": settings.MANUAL_REVIEW_THRESHOLD,
            "enable_chatgpt_enhancement": settings.ENABLE_CHATGPT_ENHANCEMENT,
            "chatgpt_enhancement_threshold": settings.CHATGPT_ENHANCEMENT_THRESHOLD
        },
        "note": "Changes are runtime only. Update .env file for persistence."
    }

@router.get("/cost-estimate")
async def estimate_validation_cost(
    num_addresses: int,
    use_chatgpt: bool = True,
    chatgpt_percentage: int = 30  # % of addresses that need ChatGPT enhancement
):
    """
    Estimate cost for validating N addresses
    """
    osm_cost = 0.0  # OSM is free
    chatgpt_cost = 0.0
    
    if use_chatgpt:
        chatgpt_addresses = int(num_addresses * (chatgpt_percentage / 100))
        validator = ChatGPTAddressValidator()
        cost_estimate = validator.estimate_cost(chatgpt_addresses)
        chatgpt_cost = cost_estimate['estimated_cost_usd']
    
    total_cost = osm_cost + chatgpt_cost
    
    return {
        "num_addresses": num_addresses,
        "breakdown": {
            "osm_nominatim": {
                "addresses": num_addresses,
                "cost_usd": osm_cost,
                "note": "FREE - OpenStreetMap Nominatim"
            },
            "chatgpt_gpt4": {
                "addresses": int(num_addresses * (chatgpt_percentage / 100)) if use_chatgpt else 0,
                "cost_usd": chatgpt_cost,
                "percentage_enhanced": chatgpt_percentage if use_chatgpt else 0,
                "note": "Only used for low-confidence records"
            }
        },
        "total_cost_usd": round(total_cost, 2),
        "cost_per_address": round(total_cost / num_addresses, 4) if num_addresses > 0 else 0
    }
