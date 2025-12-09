"""
API routes for the Know Your Company platform.
Handles company authenticity check requests and queries.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from app.models.company import CheckCompanyRequest, CheckCompanyResponse, CompanyInsight
from app.services.company_aggregator import (
    build_company_insight,
    refresh_company_insight,
    normalize_canonical_name
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["company"])


@router.post("/check-company", response_model=CheckCompanyResponse)
async def check_company(request: CheckCompanyRequest) -> CheckCompanyResponse:
    """
    Check a company's authenticity.
    
    Aggregates signals from multiple external sources and computes:
    - Authenticity score (0-100)
    - Scam risk level (low/medium/high/unknown)
    - Company type (training/edtech/staffing/it_services)
    - Warning flags
    
    Args:
        request: CheckCompanyRequest with company name and optional details
        
    Returns:
        CheckCompanyResponse with CompanyInsight data
        
    Example:
        POST /api/check-company
        {
            "name": "XYZ Training Academy",
            "website": "https://xyztraining.com",
            "country": "India",
            "category": "training"
        }
    """
    try:
        logger.info(f"Checking company: {request.name}")
        
        # Build complete insight
        insight = await build_company_insight(request)
        
        return CheckCompanyResponse(
            success=True,
            data=insight,
            message="Company analysis completed successfully"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return CheckCompanyResponse(
            success=False,
            error=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error checking company {request.name}: {e}")
        return CheckCompanyResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )


@router.get("/company/{canonical_name}", response_model=CheckCompanyResponse)
async def get_company(canonical_name: str) -> CheckCompanyResponse:
    """
    Retrieve a previously checked company's insight from cache/database.
    
    Args:
        canonical_name: Normalized company name (lowercase, spaces stripped)
        
    Returns:
        CheckCompanyResponse with CompanyInsight data or error
        
    Example:
        GET /api/company/xyz-training-academy
    """
    try:
        from app.services.repository import get_db_service
        
        db_service = get_db_service()
        insight = await db_service.get_company_by_canonical_name(canonical_name)
        
        if not insight:
            return CheckCompanyResponse(
                success=False,
                error=f"Company '{canonical_name}' not found"
            )
        
        return CheckCompanyResponse(
            success=True,
            data=insight,
            message="Company data retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving company {canonical_name}: {e}")
        return CheckCompanyResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )


@router.post("/company/{canonical_name}/refresh", response_model=CheckCompanyResponse)
async def refresh_company(canonical_name: str) -> CheckCompanyResponse:
    """
    Force refresh a company's insight, bypassing cache.
    
    Fetches fresh data from external sources and updates the record.
    
    Args:
        canonical_name: Normalized company name
        
    Returns:
        CheckCompanyResponse with updated CompanyInsight
        
    Example:
        POST /api/company/xyz-training-academy/refresh
    """
    try:
        logger.info(f"Refreshing company: {canonical_name}")
        
        insight = await refresh_company_insight(canonical_name)
        
        if not insight:
            return CheckCompanyResponse(
                success=False,
                error=f"Company '{canonical_name}' not found"
            )
        
        return CheckCompanyResponse(
            success=True,
            data=insight,
            message="Company data refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error refreshing company {canonical_name}: {e}")
        return CheckCompanyResponse(
            success=False,
            error=f"Server error: {str(e)}"
        )


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring.
    
    Returns:
        Status dict
    """
    return {
        "status": "healthy",
        "service": "Know Your Company - Company Authenticity Checker"
    }
