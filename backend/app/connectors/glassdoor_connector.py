"""
Glassdoor data connector.
Scrapes Glassdoor employer data using Apollo state extraction from HTML.
"""

import logging
import json
import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from app.models.company import SourceSignal
from app.core.config import settings

logger = logging.getLogger(__name__)

# Desktop User-Agent to avoid blocking
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


async def fetch_glassdoor_signals(company_id: int) -> list[SourceSignal]:
    """
    Fetch signals from Glassdoor for a company.
    
    Args:
        company_id: Glassdoor company ID (e.g., 1234567)
        
    Returns:
        List of SourceSignal objects from Glassdoor
    """
    signals = []
    
    try:
        logger.info(f"Fetching Glassdoor signals for company ID: {company_id}")
        
        # Glassdoor company overview URL
        url = f"https://www.glassdoor.com/Overview/Working-at-EI_IE{company_id}.htm"
        
        overview_data = await scrape_glassdoor_overview(company_id)
        
        if overview_data:
            # Create a single signal for the Glassdoor overview
            signal = SourceSignal(
                platform="glassdoor",
                url=url,
                title="Company Overview",
                rating=overview_data.get("rating"),
                review_count=overview_data.get("review_count"),
                snippet=overview_data.get("snippet")
            )
            signals.append(signal)
            logger.debug(f"Extracted Glassdoor signal: {signal}")
        
    except Exception as e:
        logger.error(f"Error fetching Glassdoor signals for company ID {company_id}: {e}")
    
    return signals


async def scrape_glassdoor_overview(company_id: int) -> Optional[dict]:
    """
    Scrape Glassdoor company overview page and extract data from Apollo state.
    
    Args:
        company_id: Glassdoor company ID
        
    Returns:
        Dict with extracted overview data or None on failure
    """
    try:
        url = f"https://www.glassdoor.com/Overview/Working-at-EI_IE{company_id}.htm"
        
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url,
                headers={"User-Agent": DESKTOP_USER_AGENT}
            )
            response.raise_for_status()
        
        # Extract Apollo state from HTML
        apollo_state = extract_apollo_state(response.text)
        
        if apollo_state:
            # Parse employer data from Apollo state
            employer_data = parse_employer_from_apollo(apollo_state)
            if employer_data:
                return employer_data
        
        return None
        
    except httpx.RequestError as e:
        logger.error(f"Glassdoor request failed for company ID {company_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error scraping Glassdoor overview for company ID {company_id}: {e}")
        return None


def extract_apollo_state(html: str) -> Optional[dict]:
    """
    Extract Apollo state JSON from Glassdoor HTML page.
    
    Apollo state is embedded in a script tag and contains all the page data.
    
    Args:
        html: HTML content of Glassdoor page
        
    Returns:
        Parsed Apollo state dict or None on failure
    """
    try:
        # Look for the Apollo state in script tags
        # Pattern: look for apolloState or __APOLLO_STATE__
        pattern = r'<script[^>]*>window\.["\']{0,2}__APOLLO_STATE__["\']{0,2}\s*=\s*(\{.*?\});?</script>'
        
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        
        if match:
            state_json = match.group(1)
            apollo_state = json.loads(state_json)
            logger.debug("Successfully extracted Apollo state from HTML")
            return apollo_state
        
        # Alternative pattern
        pattern2 = r'apolloState\s*=\s*(\{.*?\})\s*;'
        match2 = re.search(pattern2, html, re.DOTALL)
        
        if match2:
            state_json = match2.group(1)
            apollo_state = json.loads(state_json)
            logger.debug("Successfully extracted Apollo state (alternative pattern)")
            return apollo_state
        
        logger.warning("Apollo state not found in HTML")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Apollo state JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting Apollo state: {e}")
        return None


def parse_employer_from_apollo(apollo_state: dict) -> Optional[dict]:
    """
    Parse employer information from Apollo state.
    
    TODO: Refine selector logic based on actual Glassdoor Apollo state structure
    - Look for keys starting with "Employer:"
    - Extract: name, rating, reviewCount, industry, location, etc.
    - Current implementation is a stub
    
    Args:
        apollo_state: Parsed Apollo state dict
        
    Returns:
        Dict with employer data or None
    """
    try:
        # Look for employer data in Apollo cache
        # Keys are typically like "Employer:123456" or "EmployerProfile:123456"
        
        for key, value in apollo_state.items():
            if key.startswith("Employer:") and isinstance(value, dict):
                logger.debug(f"Found employer data with key: {key}")
                
                # Extract relevant fields
                rating = value.get("overallRating")
                review_count = value.get("reviewCount")
                name = value.get("name")
                
                return {
                    "name": name,
                    "rating": float(rating) if rating else None,
                    "review_count": int(review_count) if review_count else None,
                    "snippet": f"Glassdoor company: {name}" if name else None
                }
        
        logger.debug("No employer data found in Apollo state")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing employer from Apollo state: {e}")
        return None
