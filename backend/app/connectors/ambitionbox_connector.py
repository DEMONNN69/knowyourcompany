"""
AmbitionBox data connector.
Scrapes AmbitionBox company data using BeautifulSoup.
"""

import logging
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from app.models.company import SourceSignal
from app.core.config import settings

logger = logging.getLogger(__name__)

DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


async def fetch_ambitionbox_signals(company_name: str) -> list[SourceSignal]:
    """
    Fetch signals from AmbitionBox for a company.
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        List of SourceSignal objects from AmbitionBox
    """
    signals = []
    
    try:
        logger.info(f"Fetching AmbitionBox signals for: {company_name}")
        
        # AmbitionBox search/company page
        # TODO: Determine actual URL structure
        # Typically: https://www.ambitionbox.com/search?q={company_name}
        # or: https://www.ambitionbox.com/{slug}
        
        url = f"https://www.ambitionbox.com/search?q={company_name.replace(' ', '+')}"
        
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url,
                headers={"User-Agent": DESKTOP_USER_AGENT}
            )
            response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract company data
        # TODO: Refine selectors based on actual AmbitionBox HTML structure
        company_data = extract_ambitionbox_company_data(soup, company_name)
        
        if company_data:
            signal = SourceSignal(
                platform="ambitionbox",
                url=url,
                title="Company Ratings & Reviews",
                rating=company_data.get("rating"),
                review_count=company_data.get("review_count"),
                snippet=company_data.get("snippet")
            )
            signals.append(signal)
            logger.debug(f"Extracted AmbitionBox signal: {signal}")
        
    except httpx.RequestError as e:
        logger.error(f"AmbitionBox request failed for {company_name}: {e}")
    except Exception as e:
        logger.error(f"Error fetching AmbitionBox signals for {company_name}: {e}")
    
    return signals


def extract_ambitionbox_company_data(soup: BeautifulSoup, company_name: str) -> Optional[dict]:
    """
    Extract company information from AmbitionBox search/company page.
    
    TODO: Update CSS selectors based on actual page structure
    - Look for company card/listing with name, rating, and review count
    - Extract rating (usually out of 5)
    - Extract number of reviews
    - Extract snippet (company description or key info)
    
    Args:
        soup: BeautifulSoup object of the page
        company_name: Name of the company to extract
        
    Returns:
        Dict with extracted data or None
    """
    try:
        # TODO: Implement actual CSS selector logic
        # Example placeholders (these will need to be adjusted):
        
        # Look for first matching company card
        # company_card = soup.select_one('.company-card, .search-result-item')
        
        # if company_card:
        #     rating_elem = company_card.select_one('.rating, .star-rating')
        #     review_elem = company_card.select_one('.review-count, .reviews')
        #     
        #     return {
        #         "rating": float(rating_elem.text.strip()) if rating_elem else None,
        #         "review_count": int(review_elem.text.replace('K', '000')) if review_elem else None,
        #         "snippet": f"{company_name} - AmbitionBox"
        #     }
        
        logger.debug("AmbitionBox selectors not yet configured (needs manual adjustment)")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting AmbitionBox data: {e}")
        return None
