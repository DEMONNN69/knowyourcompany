"""
Company aggregator service.
Orchestrates fetching from multiple external sources, caching, and persistence.
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from app.models.company import CompanyInsight, CheckCompanyRequest, SourceSignal
from app.services.cache import get_cache_service
from app.services.repository import get_db_service
from app.services.scoring import compute_scores
from app.connectors.reddit_connector import fetch_reddit_signals
from app.connectors.x_connector import fetch_x_signals
from app.connectors.glassdoor_connector import fetch_glassdoor_signals
from app.connectors.ambitionbox_connector import fetch_ambitionbox_signals
from app.connectors.linkedin_connector import fetch_linkedin_signals
from app.core.config import settings

logger = logging.getLogger(__name__)


def normalize_canonical_name(name: str) -> str:
    """
    Normalize company name to canonical form.
    
    Converts to lowercase and strips extra whitespace.
    
    Args:
        name: Original company name
        
    Returns:
        Normalized name
    """
    return name.strip().lower()


async def build_company_insight(request: CheckCompanyRequest) -> CompanyInsight:
    """
    Build a complete company insight by aggregating signals from multiple sources.
    
    Flow:
    1. Normalize company name to canonical form
    2. Check Redis cache
    3. If cache miss:
       a. Check database for stored insight (if not stale)
       b. If no DB record or stale, fetch from all connectors in parallel
       c. Aggregate signals and compute scores
       d. Save to database and cache
    4. Return complete CompanyInsight
    
    Args:
        request: CheckCompanyRequest with company details
        
    Returns:
        Populated CompanyInsight object
    """
    
    canonical_name = normalize_canonical_name(request.name)
    logger.info(f"Building insight for: {request.name} (canonical: {canonical_name})")
    
    # Get cache and DB services
    cache_service = get_cache_service()
    db_service = get_db_service()
    
    # 1. Check cache
    cached_insight = await cache_service.get_cached_company(canonical_name)
    if cached_insight:
        logger.info(f"Cache hit for {canonical_name}")
        return cached_insight
    
    # 2. Check database
    db_insight = await db_service.get_company_by_canonical_name(canonical_name)
    if db_insight:
        # Check if insight is fresh (less than 1 day old)
        age = datetime.utcnow() - db_insight.lastCheckedAt
        if age < timedelta(hours=24):
            logger.info(f"Found fresh DB record for {canonical_name}, re-caching")
            await cache_service.set_cached_company(canonical_name, db_insight)
            return db_insight
        else:
            logger.info(f"Found stale DB record for {canonical_name}, refreshing")
    
    # 3. Fetch signals from all connectors in parallel
    logger.info(f"Fetching signals from external sources for {canonical_name}")
    
    signals = await fetch_all_signals(request)
    
    # 4. Compute scores and compile insight
    authenticity_score, scam_risk, flags, company_type = compute_scores(
        signals,
        request.name,
        request.website
    )
    
    # Build CompanyInsight object
    insight = CompanyInsight(
        name=request.name,
        canonical_name=canonical_name,
        website=request.website,
        authenticityScore=authenticity_score,
        scamRisk=scam_risk,
        companyType=company_type,
        flags=flags,
        sources=signals,
        lastCheckedAt=datetime.utcnow()
    )
    
    # 5. Save to database
    await db_service.save_company_insight(insight)
    
    # 6. Cache result
    await cache_service.set_cached_company(canonical_name, insight)
    
    logger.info(f"Completed insight for {canonical_name}")
    
    return insight


async def fetch_all_signals(request: CheckCompanyRequest) -> list[SourceSignal]:
    """
    Fetch signals from all available connectors in parallel.
    
    Handles connector failures gracefully by returning partial results.
    
    Args:
        request: Company check request
        
    Returns:
        Aggregated list of SourceSignal objects
    """
    
    all_signals: list[SourceSignal] = []
    
    # Prepare tasks for parallel execution
    tasks = []
    
    # Always include Reddit, Glassdoor, and AmbitionBox
    tasks.append(("reddit", fetch_reddit_signals(request.name)))
    tasks.append(("glassdoor", fetch_glassdoor_signals(request.name)))
    tasks.append(("ambitionbox", fetch_ambitionbox_signals(request.name)))
    
    # Include optional connectors
    tasks.append(("x", fetch_x_signals(request.name)))
    tasks.append(("linkedin", fetch_linkedin_signals(request.name)))
    
    # Execute all tasks concurrently
    results = await asyncio.gather(
        *[task[1] for task in tasks],
        return_exceptions=True
    )
    
    # Process results and handle exceptions
    for (connector_name, _), result in zip(tasks, results):
        try:
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {connector_name}: {result}")
            else:
                all_signals.extend(result)
                logger.debug(f"Fetched {len(result)} signals from {connector_name}")
        except Exception as e:
            logger.error(f"Unexpected error processing {connector_name} result: {e}")
    
    return all_signals


async def refresh_company_insight(canonical_name: str) -> Optional[CompanyInsight]:
    """
    Force refresh a company insight, bypassing cache.
    
    Args:
        canonical_name: Normalized company name
        
    Returns:
        Updated CompanyInsight or None if company not found
    """
    
    logger.info(f"Force refreshing insight for {canonical_name}")
    
    cache_service = get_cache_service()
    db_service = get_db_service()
    
    # Get original company data from DB
    db_insight = await db_service.get_company_by_canonical_name(canonical_name)
    if not db_insight:
        logger.warning(f"Company {canonical_name} not found in database")
        return None
    
    # Create request from existing data
    request = CheckCompanyRequest(
        name=db_insight.name,
        website=db_insight.website
    )
    
    # Invalidate cache and rebuild
    await cache_service.invalidate_cache(canonical_name)
    
    # Build fresh insight
    fresh_insight = await build_company_insight(request)
    
    return fresh_insight
