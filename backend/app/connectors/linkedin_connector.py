"""
LinkedIn data connector.
Checks for company profile existence and basic info using linkedin_scraper.
Currently stubbed - implement when Selenium integration is needed.
"""

import logging
from app.models.company import SourceSignal

logger = logging.getLogger(__name__)


async def fetch_linkedin_signals(company_name: str) -> list[SourceSignal]:
    """
    Fetch signals from LinkedIn about a company.
    
    TODO: Implement linkedin_scraper integration
    - Install: pip install linkedin-scraper or similar
    - Use Selenium WebDriver to:
      - Search for company on LinkedIn
      - Check if official company page exists
      - Extract: company name, URL, description, followers, industry
      - Check if page has active hiring (can infer from job postings)
    - Create SourceSignal with company existence/legitimacy indicator
    
    Note: LinkedIn scraping is sensitive to bot detection. Consider:
    - Using official LinkedIn API if available
    - Adding delays between requests
    - Rotating user agents
    - Handling CAPTCHAs appropriately
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        List of SourceSignal objects from LinkedIn
    """
    logger.debug(f"LinkedIn connector stub called for: {company_name}")
    
    # Stub: return empty list
    # This connector is optional and requires Selenium setup
    # Enable when ready: return await _fetch_linkedin_with_selenium(company_name)
    
    return []


async def _fetch_linkedin_with_selenium(company_name: str) -> list[SourceSignal]:
    """
    Actual LinkedIn scraping implementation using Selenium.
    
    TODO: Implement this when ready
    - Import selenium, webdriver, etc.
    - Set up headless browser
    - Navigate to LinkedIn company search
    - Extract data from company profile
    - Return SourceSignal objects
    
    Args:
        company_name: Name of the company
        
    Returns:
        List of SourceSignal objects
    """
    # Placeholder for actual implementation
    return []
