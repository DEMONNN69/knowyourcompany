"""
X (Twitter) data connector using Twikit.
Fetches tweets about companies.
Currently stubbed - implement when Twikit integration is needed.
"""

import logging
from app.models.company import SourceSignal

logger = logging.getLogger(__name__)


async def fetch_x_signals(company_name: str) -> list[SourceSignal]:
    """
    Fetch signals from X (Twitter) about a company using Twikit.
    
    TODO: Implement Twikit integration
    - Install: pip install twikit
    - Authenticate with X/Twitter credentials
    - Search for tweets about company using:
      - "{company_name} internship"
      - "{company_name} scam"
      - "{company_name} review"
    - Extract:
      - tweet text
      - url (tweet permalink)
      - likes/retweets (engagement)
      - sentiment (analyze from text)
    - Create SourceSignal for each relevant tweet
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        List of SourceSignal objects from X
    """
    logger.debug(f"X connector stub called for: {company_name}")
    
    # Stub: return empty list
    # This connector is optional and can be enabled later
    return []
