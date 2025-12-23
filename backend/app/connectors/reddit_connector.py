"""
Reddit data connector.
Fetches posts and comments about companies by scraping old.reddit.com.

Design notes:
- Uses requests + BeautifulSoup for search (server-rendered old.reddit.com)
- Keeps Selenium only as an optional fallback for edge cases
- Adds user-agent rotation, jittered delays, and retry/backoff
- Improves sentiment via VADER with engagement-based confidence
- Filters noisy comments ([deleted], bots, AutoModerator)
"""

import logging
import time
import re
import math
import random
import asyncio
from typing import Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except Exception:
    _vader = None

from app.models.company import SourceSignal
from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread pool for running synchronous code
_executor = ThreadPoolExecutor(max_workers=4)

# Rotating User-Agents to reduce fingerprinting
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _random_ua() -> str:
    return random.choice(_UA_POOL)


def _jitter_sleep(base: float = 0.8, spread: float = 0.7):
    """Sleep with jitter to avoid fixed timing patterns."""
    delay = max(0.1, base + random.uniform(-spread, spread))
    time.sleep(delay)


def _requests_session() -> requests.Session:
    """Configure a requests session with retry/backoff."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _setup_driver(headless=True):
    """Setup Selenium Chrome driver with optimal settings."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,800")
    options.add_argument(f"--user-agent={_random_ua()}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=options)


def _search_reddit_posts_requests(query: str, max_results: int = 5) -> List[Tuple[str, str]]:
    """Search Reddit using requests + BeautifulSoup. Returns list of (url, title)."""
    session = _requests_session()
    encoded_query = quote_plus(query)
    url = f"https://old.reddit.com/search?q={encoded_query}&sort=relevance&t=all&type=link"

    headers = {"User-Agent": _random_ua()}
    try:
        logger.info(f"Searching Reddit (requests): {url}")
        resp = session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Search request failed ({resp.status_code}) for {url}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Tuple[str, str]] = []
        seen = set()
        for a in soup.select("a.search-title"):
            href = a.get("href")
            title = (a.text or "").strip()
            if not href or "/comments/" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            results.append((href, title))
            if len(results) >= max_results:
                break

        logger.info(f"Found {len(results)} posts for query: {query}")
        _jitter_sleep(0.6, 0.5)
        return results
    except Exception as e:
        logger.error(f"Error searching Reddit via requests: {e}")
        return []


def _search_reddit_posts_selenium(query: str, max_results=5, headless=True) -> List[Tuple[str, str]]:
    """Selenium fallback search. Returns list of (url, title)."""
    driver = None
    try:
        driver = _setup_driver(headless=headless)
        encoded_query = quote_plus(query)
        search_url = f"https://old.reddit.com/search/?q={encoded_query}&sort=relevance&type=link&t=all"

        logger.info(f"Searching Reddit (selenium): {search_url}")
        driver.get(search_url)
        _jitter_sleep(1.2, 0.6)

        try:
            consent_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Accept') or contains(., 'I agree')]")
            if consent_buttons:
                consent_buttons[0].click()
                _jitter_sleep(0.8, 0.4)
        except Exception:
            pass

        collected: List[Tuple[str, str]] = []
        seen_urls = set()

        for _ in range(2):
            links = driver.find_elements(By.CSS_SELECTOR, "a.search-title")
            for link_elem in links:
                href = link_elem.get_attribute("href")
                title = link_elem.text.strip()
                if href and "/comments/" in href and href not in seen_urls:
                    seen_urls.add(href)
                    collected.append((href, title))
                    if len(collected) >= max_results:
                        break
            if len(collected) >= max_results:
                break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _jitter_sleep(1.0, 0.6)

        logger.info(f"Found {len(collected)} posts for query (selenium): {query}")
        return collected[:max_results]
    except Exception as e:
        logger.error(f"Error searching Reddit (selenium): {e}")
        return []
    finally:
        if driver:
            driver.quit()


def _fetch_post_details(post_url: str):
    """
    Fetch post details and comments from old.reddit.com.
    Returns dict with title, score, num_comments, comments_text.
    """
    # Ensure we use old.reddit.com
    post_url = re.sub(r"^https?://(www|new|np)\.reddit\.com", "https://old.reddit.com", post_url)
    
    headers = {"User-Agent": _random_ua()}
    
    try:
        logger.debug(f"Fetching post: {post_url}")
        session = _requests_session()
        response = session.get(post_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {post_url} (status {response.status_code})")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract post metadata
        title_elem = soup.select_one("a.title")
        title = title_elem.text.strip() if title_elem else "Unknown"
        
        # Extract score
        score = 0
        score_elem = soup.select_one("div.score.unvoted")
        if score_elem:
            score_text = score_elem.get("title", "0")
            try:
                score = int(score_text)
            except ValueError:
                pass
        
        # Extract comments (prefer top-level, filter noise)
        comments: List[str] = []
        comment_area = soup.select_one("div.commentarea")
        if comment_area:
            for comment_div in comment_area.select("div.entry"):
                # Skip AutoModerator/bots
                author = None
                tagline = comment_div.select_one("p.tagline a.author")
                if tagline:
                    author = (tagline.text or "").strip()
                if author and author.lower() in {"automoderator"}:
                    continue
                body_elem = comment_div.select_one("form div.md")
                if not body_elem:
                    continue
                text = body_elem.get_text("\n").strip()
                if not text:
                    continue
                tl = text.lower()
                if tl in {"[deleted]", "[removed]"}:
                    continue
                if "i am a bot" in tl or "bot" in tl and "help" in tl:
                    continue
                if len(text) <= 10:
                    continue
                comments.append(text)
        
        # Get number of comments from post info
        num_comments = len(comments)
        comments_elem = soup.select_one("a.comments")
        if comments_elem:
            comments_text = comments_elem.text
            match = re.search(r'(\d+)', comments_text)
            if match:
                num_comments = int(match.group(1))
        
        return {
            "title": title,
            "url": post_url,
            "score": score,
            "num_comments": num_comments,
            "comments": comments[:20],  # Limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching post details from {post_url}: {e}")
        return None


def _analyze_sentiment(comments: list[str], score: int, num_comments: int) -> Tuple[str, float]:
    """
    Analyze sentiment using VADER if available; fallback to neutral.
    Returns (sentiment_label, confidence).
    """
    if not comments:
        # No comments → neutral with low confidence; lightly consider score
        base = "neutral"
        if score and score > 200:
            base = "positive"
        elif score and score < -20:
            base = "negative"
        return base, 0.2

    if _vader:
        compounds = []
        for c in comments[:15]:
            try:
                compounds.append(_vader.polarity_scores(c)["compound"])
            except Exception:
                continue
        if not compounds:
            return "neutral", 0.3
        avg = sum(compounds) / len(compounds)
        # Label thresholds per VADER guidance
        if avg >= 0.05:
            label = "positive"
        elif avg <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        # Engagement-based confidence (log scale)
        conf = min(1.0, math.log1p(max(0, num_comments)) / 3.0)
        return label, conf

    # Fallback: neutral with minimal confidence
    return "neutral", 0.2


def _scrape_reddit_for_company(company_name: str, max_posts_per_query=3, use_selenium_fallback: bool = False):
    """
    Synchronous function to scrape Reddit for company information.
    Searches multiple query variations and returns list of post details.
    """
    queries = [
        f'"{company_name}" internship',
        f'"{company_name}" hiring',
        f'"{company_name}" review',
        f'"{company_name}" experience',
    ]
    
    all_results = []
    seen_urls = set()
    
    failed_queries = 0
    for query in queries:
        try:
            logger.info(f"Searching Reddit with query: {query}")
            posts = _search_reddit_posts_requests(query, max_results=max_posts_per_query)
            if not posts and use_selenium_fallback:
                logger.info("No results via requests; trying Selenium fallback...")
                posts = _search_reddit_posts_selenium(query, max_results=max_posts_per_query, headless=True)
            
            for post_url, title in posts:
                if post_url in seen_urls:
                    continue
                seen_urls.add(post_url)
                
                # Fetch post details
                details = _fetch_post_details(post_url)
                if details:
                    all_results.append(details)
                
                # Polite jitter
                _jitter_sleep(0.9, 0.7)
                
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            failed_queries += 1
            continue
    logger.info(f"Scrape summary for '{company_name}': results={len(all_results)} failed_queries={failed_queries}")
    return all_results


async def fetch_reddit_signals(company_name: str) -> list[SourceSignal]:
    """
    Fetch signals from Reddit about a company by scraping old.reddit.com.
    
    Searches for posts matching:
    - "{company_name} internship"
    - "{company_name} hiring"
    - "{company_name} review"
    - "{company_name} experience"
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        List of SourceSignal objects from Reddit
    """
    signals = []
    
    try:
        logger.info(f"Fetching Reddit signals for: {company_name}")
        
        # Run the scraping in a thread pool since it's synchronous
        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(_executor, _scrape_reddit_for_company, company_name, 3, False)
        except RuntimeError:
            # In case no running loop (older environments), fallback
            results = await asyncio.to_thread(_scrape_reddit_for_company, company_name, 3, False)
        
        # Convert results to SourceSignal objects
        for post_data in results:
            try:
                # Create snippet from comments
                snippet = post_data["title"]
                if post_data["comments"]:
                    # Add first comment as context
                    first_comment = post_data["comments"][0][:200]
                    snippet += f"\n\nTop comment: {first_comment}..."
                
                # Analyze sentiment
                label, confidence = _analyze_sentiment(
                    post_data["comments"],
                    post_data["score"],
                    post_data["num_comments"]
                )
                # Map VADER label to model's allowed sentiment literals
                sentiment_literal = {
                    "positive": "pos",
                    "negative": "neg",
                    "neutral": "neutral",
                }.get(label, "neutral")

                signal = SourceSignal(
                    platform="reddit",
                    url=post_data["url"],
                    title=post_data["title"],
                    snippet=snippet,
                    sentiment=sentiment_literal,
                    review_count=post_data["num_comments"],
                )
                signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error creating signal from post data: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(signals)} Reddit signals for {company_name}")
        
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
