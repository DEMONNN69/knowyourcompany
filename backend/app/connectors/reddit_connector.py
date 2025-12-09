"""
Reddit data connector.
Fetches posts and comments about companies using Reddit's official API.
"""

import logging
from typing import Optional
import httpx
from datetime import datetime

from app.models.company import SourceSignal
from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_reddit_signals(company_name: str) -> list[SourceSignal]:
    """
    Fetch signals from Reddit about a company.
    
    Searches for posts matching:
    - "{company_name} internship"
    - "{company_name} scam"
    - "{company_name} review"
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        List of SourceSignal objects from Reddit
    """
    signals = []
    
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        logger.warning("Reddit credentials not configured. Skipping Reddit connector.")
        return signals
    
    try:
        # TODO: Implement Reddit API authentication and search
        # 1. Use httpx to authenticate with Reddit API
        # 2. Get bearer token using client credentials
        # 3. Search for queries:
        #    - "{company_name} internship"
        #    - "{company_name} scam"
        #    - "{company_name} review"
        # 4. For each relevant post, extract:
        #    - title
        #    - url (post permalink)
        #    - snippet (post text/selftext)
        #    - score (upvotes - downvotes)
        #    - sentiment (analyze from comments/score)
        # 5. Create SourceSignal for each post
        
        logger.info(f"Fetching Reddit signals for: {company_name}")
        
        # Stub implementation returning empty list
        # Remove this when implementing actual Reddit API calls
        
    except httpx.RequestError as e:
        logger.error(f"Reddit API request failed: {e}")
    except Exception as e:
        logger.error(f"Error fetching Reddit signals for {company_name}: {e}")
    
    return signals


async def get_reddit_credentials() -> Optional[dict]:
    """
    Get Reddit API credentials from configuration.
    
    Returns:
        Dict with client_id and client_secret, or None if not configured
    """
    if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
        return {
            "client_id": settings.REDDIT_CLIENT_ID,
            "client_secret": settings.REDDIT_CLIENT_SECRET,
            "user_agent": settings.REDDIT_USER_AGENT,
        }
    return None
