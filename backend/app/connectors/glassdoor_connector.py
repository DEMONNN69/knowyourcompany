"""
Glassdoor data connector.
Scrapes Glassdoor employer data using Apollo state extraction from HTML.
Includes mock data fallback for testing.
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

# Company name to Glassdoor ID mapping
COMPANY_ID_MAP = {
    "infosys": 7927,
    "tcs": 1353,
    "tata consultancy services": 1353,
    "wipro": 8833,
    "accenture": 2627,
    "cognizant": 2211,
    "capgemini": 1231,
    "google": 9079,
    "amazon": 6036,
    "microsoft": 1651,
    "apple": 1138,
    "meta": 1018,
    "ibm": 1103,
    "deloitte": 2347,
}




async def fetch_glassdoor_signals(company_name: str, company_id: Optional[int] = None) -> list[SourceSignal]:
    """
    Fetch signals from Glassdoor for a company.
    
    First tries to use actual company_id, then maps from company name.
    Attempts real scraping with graceful fallback to mock data for testing.
    
    Args:
        company_name: Company name (used for mapping if company_id not provided)
        company_id: Optional Glassdoor company ID
        
    Returns:
        List of SourceSignal objects from Glassdoor
    """
    signals = []
    
    # Try to get company ID from mapping if not provided
    if not company_id:
        company_id = COMPANY_ID_MAP.get(company_name.lower().strip())
    
    if not company_id:
        logger.debug(f"No Glassdoor ID mapping found for: {company_name}")
        return signals
    
    try:
        logger.info(f"Fetching Glassdoor signals for: {company_name} (ID: {company_id})")
        
        # Try to scrape real data from Glassdoor
        overview_data = await scrape_glassdoor_overview(company_id)
        
        if overview_data:
            # Create a single signal for the Glassdoor overview
            url = f"https://www.glassdoor.com/Overview/Working-at-EI_IE{company_id}.htm"
            
            signal = SourceSignal(
                platform="glassdoor",
                url=url,
                title=f"{overview_data.get('name', company_name)} - Glassdoor Overview",
                rating=overview_data.get("rating"),
                review_count=overview_data.get("review_count"),
                snippet=overview_data.get("snippet", f"Glassdoor rating: {overview_data.get('rating', 'N/A')}/5.0")
            )
            signals.append(signal)
            logger.info(f"✓ Added Glassdoor signal for {company_name} - Rating: {overview_data.get('rating')}")
        
    except Exception as e:
        logger.error(f"Error fetching Glassdoor signals: {e}")
    
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
        
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": DESKTOP_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Referer": "https://www.glassdoor.com/",
                }
            )
            response.raise_for_status()
        
        html = response.text
        
        # Try to extract from Apollo state first
        apollo_state = extract_apollo_state(html)
        if apollo_state:
            employer_data = parse_employer_from_apollo(apollo_state)
            if employer_data:
                logger.info(f"Successfully scraped real data for company ID {company_id}")
                return employer_data
        
        # Fallback: Parse HTML structure directly
        data = scrape_html_structure(html, company_id)
        if data:
            logger.info(f"Successfully scraped real data from HTML for company ID {company_id}")
            return data
        
        logger.warning(f"Could not extract data from Glassdoor for company ID {company_id}")
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
    Tries multiple patterns to find the state object.
    
    Args:
        html: HTML content of Glassdoor page
        
    Returns:
        Parsed Apollo state dict or None on failure
    """
    try:
        # Pattern 1: __APOLLO_STATE__ in script tag
        pattern1 = r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});?\s*(?:</script>|window\.)'
        match = re.search(pattern1, html, re.DOTALL)
        if match:
            try:
                state_json = match.group(1)
                apollo_state = json.loads(state_json)
                logger.debug("Successfully extracted Apollo state (pattern 1)")
                return apollo_state
            except json.JSONDecodeError:
                logger.debug("Pattern 1 matched but JSON decode failed")
        
        # Pattern 2: apolloCache in script tag
        pattern2 = r'window\.apolloCache\s*=\s*(\{.*?\});?\s*(?:</script>|window\.)'
        match = re.search(pattern2, html, re.DOTALL)
        if match:
            try:
                state_json = match.group(1)
                apollo_state = json.loads(state_json)
                logger.debug("Successfully extracted Apollo state (pattern 2)")
                return apollo_state
            except json.JSONDecodeError:
                logger.debug("Pattern 2 matched but JSON decode failed")
        
        # Pattern 3: Look in all script tags for JSON-like structures
        script_pattern = r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for script_content in scripts:
            try:
                data = json.loads(script_content)
                if isinstance(data, dict) and any(
                    key.startswith('Employer') or key.startswith('employer') 
                    for key in data.keys()
                ):
                    logger.debug("Successfully extracted Apollo state from JSON script tag")
                    return data
            except json.JSONDecodeError:
                continue
        
        logger.debug("Apollo state not found in HTML")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting Apollo state: {e}")
        return None


def parse_employer_from_apollo(apollo_state: dict) -> Optional[dict]:
    """
    Parse employer information from Apollo state.
    
    Extracts name, rating, review count from Glassdoor's Apollo state structure.
    
    Args:
        apollo_state: Parsed Apollo state dict
        
    Returns:
        Dict with employer data or None
    """
    try:
        # Look for employer data in Apollo cache
        # Keys are typically like "Employer:123456" or "EmployerProfile:123456"
        
        for key, value in apollo_state.items():
            if isinstance(value, dict) and key.startswith("Employer"):
                logger.debug(f"Found employer data with key: {key}")
                
                # Extract relevant fields - handle different key names
                rating = value.get("overallRating") or value.get("overall_rating") or value.get("rating")
                review_count = value.get("reviewCount") or value.get("review_count") or value.get("numReviews")
                name = value.get("name") or value.get("companyName")
                industry = value.get("industry")
                
                if rating or name:
                    return {
                        "name": name,
                        "rating": float(rating) if rating else None,
                        "review_count": int(review_count) if review_count else None,
                        "industry": industry,
                        "snippet": f"Glassdoor rating: {rating}/5.0" if rating else "Company on Glassdoor"
                    }
        
        logger.debug("No employer data found in Apollo state")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing employer from Apollo state: {e}")
        return None


def scrape_html_structure(html: str, company_id: int) -> Optional[dict]:
    """
    Parse Glassdoor data directly from HTML structure using BeautifulSoup.
    
    Falls back to mock data if real scraping returns no data.
    
    Args:
        html: HTML content of Glassdoor page
        company_id: Company ID (for fallback to mock data)
        
    Returns:
        Dict with company data or None
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for rating in various places
        rating = None
        review_count = None
        company_name = None
        
        # Look for company name in title or header
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            text = title_tag.get_text()
            if ' - ' in text:
                company_name = text.split(' - ')[0].strip()
        
        # Try to find rating data in script tags (JSON-LD or similar)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'ratingValue' in data:
                        rating = float(data.get('ratingValue'))
                    if 'reviewCount' in data or 'numberOfReviews' in data:
                        review_count = int(data.get('reviewCount') or data.get('numberOfReviews'))
                    if 'name' in data:
                        company_name = data.get('name')
            except Exception as e:
                logger.debug(f"Could not parse JSON-LD: {e}")
        
        # Look for rating in data attributes and spans
        if not rating:
            # Look for elements with rating values
            rating_patterns = [
                soup.find(attrs={'data-test': 'employer-rating'}),
                soup.find('span', class_=re.compile(r'rating', re.I)),
                soup.find(attrs={'class': re.compile(r'rating', re.I)}),
            ]
            for elem in rating_patterns:
                if elem:
                    try:
                        rating_text = elem.get_text(strip=True)
                        rating = float(rating_text.split()[0])
                        break
                    except (ValueError, IndexError):
                        pass
        
        # Look for review count - search more thoroughly
        if not review_count:
            # Look for review count in various elements
            for elem in soup.find_all(['span', 'div', 'p']):
                text = elem.get_text(strip=True).lower()
                # Match patterns like "12,450 reviews" or "12450 reviews"
                match = re.search(r'([\d,]+)\s*reviews?', text)
                if match:
                    try:
                        review_count = int(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        pass
        
        # Return data if we found rating or company name
        if rating or company_name:
            return {
                "name": company_name,
                "rating": rating,
                "review_count": review_count,
                "snippet": f"Glassdoor rating: {rating}/5.0" if rating else None
            }
        
        # Nothing found in HTML
        logger.debug(f"No data extracted from HTML for company ID {company_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping HTML structure: {e}")
        return None
