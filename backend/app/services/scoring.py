"""
Rule-based scoring and heuristic analysis for company authenticity.
Computes authenticity score, scam risk, company type, and flags.
"""

import logging
from typing import Literal
from app.models.company import SourceSignal

logger = logging.getLogger(__name__)

# Keyword lists for sentiment analysis
NEGATIVE_KEYWORDS = [
    "scam", "fraud", "fake", "unpaid", "no stipend",
    "certificate only", "pay to", "waste of time", "regret",
    "never hire", "avoid", "terrible", "worst", "ripoff",
    "deceptive", "misleading", "false promises"
]

POSITIVE_KEYWORDS = [
    "good learning", "helpful", "supportive", "got stipend",
    "valuable", "recommended", "genuine", "legit", "trustworthy",
    "professional", "excellent", "great experience", "worth it"
]

# Company type indicators
TRAINING_KEYWORDS = ["training", "course", "bootcamp", "academy", "institute", "coaching"]
STAFFING_KEYWORDS = ["recruitment", "staffing", "manpower", "placement", "placement agency"]
EDTECH_KEYWORDS = ["edtech", "online learning", "e-learning", "digital learning", "skill"]
IT_SERVICES_KEYWORDS = ["it services", "software development", "consulting", "tech solutions"]

# Scam risk indicators
SCAM_INDICATORS = [
    "no linkedin page", "course marketed as internship", "hidden fees",
    "no company verification", "high negative sentiment", "no online presence"
]


def compute_scores(
    signals: list[SourceSignal],
    company_name: str,
    website: str | None = None
) -> tuple[float, Literal["low", "medium", "high", "unknown"], list[str], str | None]:
    """
    Compute authenticity score, scam risk level, flags, and company type.
    
    Algorithm:
    1. Analyze sentiment from signal snippets using keyword matching
    2. Extract ratings from Glassdoor and AmbitionBox
    3. Count positive vs negative signals
    4. Check for red flags (e.g., no LinkedIn page)
    5. Compute weighted authenticity score (0-100)
    6. Derive scam risk from score and flags
    7. Infer company type from signals and keywords
    
    Args:
        signals: List of SourceSignal objects from external sources
        company_name: Original company name (for context)
        website: Optional website URL (to check online presence)
        
    Returns:
        Tuple of (authenticityScore, scamRisk, flags, companyType)
    """
    
    flags = []
    sentiment_scores = []
    ratings = []
    signal_count = 0
    
    # Analyze each signal
    for signal in signals:
        signal_count += 1
        
        # Extract sentiment from snippet
        if signal.snippet:
            sentiment = analyze_sentiment(signal.snippet)
            sentiment_scores.append(sentiment)
        
        # Collect ratings from review platforms
        if signal.rating and signal.platform in ["glassdoor", "ambitionbox"]:
            ratings.append(signal.rating)
    
    # Compute base authenticity score
    authenticity_score = 50.0  # Start at neutral
    
    # Adjust based on sentiment
    if sentiment_scores:
        pos_count = sum(1 for s in sentiment_scores if s > 0)
        neg_count = sum(1 for s in sentiment_scores if s < 0)
        
        sentiment_ratio = (pos_count - neg_count) / len(sentiment_scores)
        authenticity_score += sentiment_ratio * 25  # ±25 points for sentiment
    
    # Adjust based on platform ratings
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        rating_score = (avg_rating / 5.0) * 25  # Normalize 0-5 to 0-25
        authenticity_score += rating_score
    
    # Penalty for lack of signals
    if signal_count == 0:
        flags.append("no external signals found")
        authenticity_score = 20.0  # Low confidence
    elif signal_count < 3:
        flags.append("limited external signals")
        authenticity_score *= 0.9  # 10% penalty
    
    # Check for specific red flags
    has_glassdoor = any(s.platform == "glassdoor" for s in signals)
    has_linkedin = any(s.platform == "linkedin" for s in signals)
    has_reddit = any(s.platform == "reddit" for s in signals)
    
    if not has_linkedin:
        flags.append("no_linkedin_page")
    
    if not has_glassdoor:
        flags.append("no_glassdoor_presence")
    
    # Check if website exists and is responsive
    if not website:
        flags.append("no_website_provided")
    
    # Infer company type
    company_type = infer_company_type(signals, company_name)
    
    # Apply type-specific flags
    if company_type == "training" or company_type == "edtech":
        # Check for "course marketed as internship" pattern
        for signal in signals:
            if signal.snippet and any(
                kw in signal.snippet.lower() for kw in ["course", "training"]
            ):
                if signal.snippet and any(
                    kw in signal.snippet.lower() for kw in ["internship", "placement"]
                ):
                    flags.append("course_marketed_as_internship")
                    break
    
    # Determine scam risk
    scam_risk = determine_scam_risk(authenticity_score, flags)
    
    # Clamp authenticity score to 0-100 range
    authenticity_score = max(0.0, min(100.0, authenticity_score))
    
    logger.info(
        f"Computed scores for {company_name}: "
        f"authenticity={authenticity_score:.1f}, risk={scam_risk}, "
        f"type={company_type}, flags={flags}"
    )
    
    return authenticity_score, scam_risk, flags, company_type


def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of a text snippet using keyword matching.
    
    Returns:
        Sentiment score: -1.0 (negative) to 1.0 (positive), 0 = neutral
    """
    text_lower = text.lower()
    
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    
    return (positive_count - negative_count) / total


def infer_company_type(signals: list[SourceSignal], company_name: str) -> str | None:
    """
    Infer company type from signals and company name keywords.
    
    Returns:
        Company type string: "training", "edtech", "staffing", "it_services", or None
    """
    # Combine text from signals and company name
    combined_text = (company_name + " " + " ".join(
        s.snippet or "" for s in signals if s.snippet
    )).lower()
    
    # Check keywords in order of specificity
    if any(kw in combined_text for kw in TRAINING_KEYWORDS):
        return "training"
    if any(kw in combined_text for kw in EDTECH_KEYWORDS):
        return "edtech"
    if any(kw in combined_text for kw in STAFFING_KEYWORDS):
        return "staffing"
    if any(kw in combined_text for kw in IT_SERVICES_KEYWORDS):
        return "it_services"
    
    return None


def determine_scam_risk(
    authenticity_score: float,
    flags: list[str]
) -> Literal["low", "medium", "high", "unknown"]:
    """
    Determine scam risk level based on authenticity score and flags.
    
    Args:
        authenticity_score: Score from 0-100
        flags: List of warning flags
        
    Returns:
        Risk level: "low", "medium", "high", or "unknown"
    """
    # Check for critical scam indicators
    critical_flags = [
        "course_marketed_as_internship",
        "no_external_signals_found"
    ]
    
    if any(flag in flags for flag in critical_flags):
        return "high"
    
    # Score-based thresholds
    if authenticity_score >= 75:
        return "low"
    elif authenticity_score >= 50:
        return "medium"
    elif authenticity_score >= 25:
        return "high"
    else:
        # Very low score with multiple flags = high risk
        if len(flags) >= 3:
            return "high"
        return "unknown"
