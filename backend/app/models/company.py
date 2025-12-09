"""
Core data models for company insights and source signals.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class SourceSignal(BaseModel):
    """
    Represents a single data point from an external source about a company.
    """
    platform: Literal["reddit", "x", "glassdoor", "ambitionbox", "linkedin", "manual"]
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)  # 0-5 scale or None
    review_count: Optional[int] = Field(None, ge=0)
    sentiment: Optional[Literal["pos", "neg", "mixed", "neutral"]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "platform": "glassdoor",
                "url": "https://www.glassdoor.com/Overview/Working-at-Company-EI_IE123.htm",
                "title": "Company Overview",
                "rating": 3.8,
                "review_count": 450,
                "sentiment": "mixed"
            }
        }


class CompanyInsight(BaseModel):
    """
    Complete authenticity check result for a company.
    Aggregates signals from multiple sources and applies scoring rules.
    """
    name: str
    canonical_name: str  # Normalized name (lowercase, stripped)
    website: Optional[str] = None
    authenticityScore: Optional[float] = Field(None, ge=0.0, le=100.0)
    scamRisk: Literal["low", "medium", "high", "unknown"] = "unknown"
    companyType: Optional[str] = None  # e.g., "edtech", "training", "staffing", "it_services"
    flags: list[str] = Field(default_factory=list)  # e.g., ["course_marketed_as_internship"]
    sources: list[SourceSignal] = Field(default_factory=list)
    lastCheckedAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "XYZ Training Academy",
                "canonical_name": "xyz training academy",
                "website": "https://xyztraining.com",
                "authenticityScore": 42.5,
                "scamRisk": "high",
                "companyType": "training",
                "flags": ["course_marketed_as_internship", "no_linkedin_page"],
                "sources": [],
                "lastCheckedAt": "2025-12-09T10:00:00Z"
            }
        }


class CheckCompanyRequest(BaseModel):
    """Request payload for checking a company's authenticity."""
    name: str = Field(..., min_length=1, description="Company name")
    website: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None  # e.g., "edtech", "training", "staffing"
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "XYZ Training Academy",
                "website": "https://xyztraining.com",
                "country": "India",
                "category": "training"
            }
        }


class CheckCompanyResponse(BaseModel):
    """Response wrapper for company authenticity check."""
    success: bool
    data: Optional[CompanyInsight] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "name": "XYZ Training Academy",
                    "canonical_name": "xyz training academy",
                    "authenticityScore": 42.5,
                    "scamRisk": "high",
                    "flags": ["course_marketed_as_internship"]
                },
                "message": "Analysis complete"
            }
        }
