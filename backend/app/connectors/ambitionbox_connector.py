"""
AmbitionBox data connector.
Scrapes AmbitionBox company data using BeautifulSoup.

Approach:
1) Fetch search page and locate first reviews link (e.g. /reviews/<slug>-reviews)
2) Fetch reviews page and parse rating/review_count via JSON-LD or text fallback
3) Emit SourceSignal with platform="ambitionbox", rating, review_count
"""

import logging
import re
import json
from typing import Optional, Tuple
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

AMBITIONBOX_BASE = "https://www.ambitionbox.com"


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

        search_q = company_name.replace(" ", "+")
        search_url = f"{AMBITIONBOX_BASE}/search?q={search_q}"

        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(
                search_url,
                headers={"User-Agent": DESKTOP_USER_AGENT, "Accept": "text/html"}
            )
            response.raise_for_status()

        reviews_url = _find_reviews_link(response.text)
        if not reviews_url:
            logger.debug("No AmbitionBox reviews link found on search page")
            return signals

        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
            reviews_resp = await client.get(
                reviews_url,
                headers={"User-Agent": DESKTOP_USER_AGENT, "Accept": "text/html"}
            )
            reviews_resp.raise_for_status()

        rating, review_count, display_name = _parse_reviews_page(reviews_resp.text)

        if rating is None and review_count is None:
            logger.debug("AmbitionBox page parsed but no rating/reviews extracted")
            return signals

        title = f"{display_name or company_name} - AmbitionBox Reviews"
        snippet = (
            f"AmbitionBox rating: {rating}/5.0" if rating is not None else "Company on AmbitionBox"
        )

        signals.append(
            SourceSignal(
                platform="ambitionbox",
                url=reviews_url,
                title=title,
                rating=rating,
                review_count=review_count,
                snippet=snippet,
            )
        )
        logger.info(f"✓ Added AmbitionBox signal for {company_name} - Rating: {rating}, Reviews: {review_count}")
        
    except httpx.RequestError as e:
        logger.error(f"AmbitionBox request failed for {company_name}: {e}")
    except Exception as e:
        logger.error(f"Error fetching AmbitionBox signals for {company_name}: {e}")
    
    return signals


def _find_reviews_link(html: str) -> Optional[str]:
    """Find the first reviews page link from the search HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.match(r"^/reviews/.+-reviews$", href):
                return f"{AMBITIONBOX_BASE}{href}"
        return None
    except Exception:
        return None


def _parse_reviews_page(html: str) -> Tuple[Optional[float], Optional[int], Optional[str]]:
    """Extract rating, review_count, and display name from reviews page HTML."""
    # 1) JSON-LD aggregateRating
    rating, reviews, name = _extract_from_jsonld(html)
    if rating is not None or reviews is not None:
        return rating, reviews, name

    # 2) Fallback patterns in text
    try:
        soup = BeautifulSoup(html, "html.parser")
        if not name:
            h1 = soup.find("h1")
            title = soup.find("title")
            name_text = h1.get_text(strip=True) if h1 else (title.get_text(strip=True) if title else None)
            if name_text and " - " in name_text:
                name = name_text.split(" - ")[0].strip()

        rating_val = None
        for elem in soup.find_all(["div", "span"], string=True):
            text = elem.get_text(strip=True).lower()
            if "rating" in text:
                m = re.search(r"(\d\.\d)\b", text)
                if m:
                    try:
                        rating_val = float(m.group(1))
                        break
                    except ValueError:
                        pass

        reviews_val = None
        for elem in soup.find_all(["div", "span", "p"], string=True):
            text = elem.get_text(strip=True).lower()
            m = re.search(r"([\d,]+)\s+reviews", text)
            if m:
                try:
                    reviews_val = int(m.group(1).replace(",", ""))
                    break
                except ValueError:
                    pass

        return rating_val, reviews_val, name
    except Exception:
        return None, None, name


def _extract_from_jsonld(html: str) -> Tuple[Optional[float], Optional[int], Optional[str]]:
    """Parse JSON-LD looking for aggregateRating and name."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue

            def extract(obj: dict) -> Tuple[Optional[float], Optional[int], Optional[str]]:
                name = obj.get("name")
                agg = obj.get("aggregateRating")
                rating = None
                reviews = None
                if isinstance(agg, dict):
                    rv = agg.get("ratingValue")
                    rc = agg.get("reviewCount") or agg.get("ratingCount")
                    try:
                        rating = float(rv) if rv is not None else None
                    except (TypeError, ValueError):
                        rating = None
                    try:
                        reviews = int(rc) if rc is not None else None
                    except (TypeError, ValueError):
                        reviews = None
                return rating, reviews, name

            if isinstance(data, dict):
                r, c, n = extract(data)
                if r is not None or c is not None:
                    return r, c, n
            elif isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    r, c, n = extract(item)
                    if r is not None or c is not None:
                        return r, c, n
        return None, None, None
    except Exception:
        return None, None, None
