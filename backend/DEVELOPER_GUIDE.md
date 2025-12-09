# Backend Developer Quick Reference

## Architecture Overview

```
┌─────────────────┐
│  React Frontend │
└────────┬────────┘
         │ HTTP
┌────────▼────────────────────────────────┐
│        FastAPI Application              │
│  ┌──────────────────────────────────┐   │
│  │     API Routes (routes.py)       │   │
│  │  - POST /api/check-company       │   │
│  │  - GET  /api/company/{name}      │   │
│  │  - POST /api/company/{name}/...  │   │
│  └──────────────────────────────────┘   │
│               ▲                          │
│               │                          │
│  ┌────────────┴──────────────────────┐  │
│  │   Company Aggregator              │  │
│  │  (orchestrates everything)        │  │
│  └────────────┬───────────────────────┘  │
│      ┌────────┴─────────────────┐        │
│      │                          │        │
│ ┌────▼─────────┐       ┌────────▼────┐  │
│ │ Cache Service │       │  Repository │  │
│ │ (Redis)       │       │  (DB)       │  │
│ └──────────────┘       └─────────────┘  │
│      ▲                       ▲            │
│      │                       │            │
│ ┌────┴────────────────────────┴──────┐  │
│ │  Connectors (parallel execution)   │  │
│ │  ├─ Reddit                         │  │
│ │  ├─ Glassdoor                      │  │
│ │  ├─ AmbitionBox                    │  │
│ │  ├─ LinkedIn                       │  │
│ │  └─ X/Twitter                      │  │
│ └────────────────────────────────────┘  │
│               ▼                          │
│  ┌──────────────────────────────────┐   │
│  │   Scoring Service                │   │
│  │   (keyword analysis, heuristics) │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
         │                 │
         │                 │
    ┌────▼──────┐  ┌──────▼──────┐
    │   Redis   │  │  PostgreSQL/ │
    │  (Cache)  │  │  Firestore   │
    └───────────┘  └──────────────┘
```

## Key Modules

### 1. Models (`app/models/company.py`)

**SourceSignal**: Individual data point from external source
```python
SourceSignal(
    platform: Literal["reddit", "x", "glassdoor", ...],
    url: str,
    title: Optional[str],
    snippet: Optional[str],
    rating: Optional[float],  # 0-5
    review_count: Optional[int],
    sentiment: Optional[Literal["pos", "neg", "mixed", "neutral"]]
)
```

**CompanyInsight**: Complete analysis result
```python
CompanyInsight(
    name: str,
    canonical_name: str,  # normalized
    authenticityScore: Optional[float],  # 0-100
    scamRisk: Literal["low", "medium", "high", "unknown"],
    companyType: Optional[str],  # "training", "edtech", etc.
    flags: list[str],  # ["course_marketed_as_internship", ...]
    sources: list[SourceSignal],
    lastCheckedAt: datetime
)
```

### 2. Services

#### Cache Service (`app/services/cache.py`)
```python
cache_service = get_cache_service()
await cache_service.get_cached_company(canonical_name)
await cache_service.set_cached_company(canonical_name, insight)
```

#### Repository (`app/services/repository.py`)
```python
db_service = get_db_service()  # Auto-selects based on config
await db_service.get_company_by_canonical_name(canonical_name)
await db_service.save_company_insight(insight)
```

#### Scoring (`app/services/scoring.py`)
```python
score, risk, flags, company_type = compute_scores(
    signals,
    company_name,
    website
)
```

#### Aggregator (`app/services/company_aggregator.py`)
```python
insight = await build_company_insight(CheckCompanyRequest(...))
```

### 3. Connectors

Each connector is independent and can fail without breaking the system:

```python
# All return list[SourceSignal]
await fetch_reddit_signals(company_name)
await fetch_glassdoor_signals(company_id)
await fetch_ambitionbox_signals(company_name)
await fetch_x_signals(company_name)
await fetch_linkedin_signals(company_name)
```

### 4. Configuration (`app/core/config.py`)

All settings loaded from environment:
```python
from app.core.config import settings

settings.DEBUG
settings.REDIS_URL
settings.CACHE_TTL_SECONDS
settings.DATABASE_URL
settings.REDDIT_CLIENT_ID
```

## Common Tasks

### Running the Server

```bash
# Development with auto-reload
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing an Endpoint

```bash
# Check a company
curl -X POST http://localhost:8000/api/check-company \
  -H "Content-Type: application/json" \
  -d '{
    "name": "XYZ Training",
    "website": "https://xyztraining.com",
    "category": "training"
  }'

# View API docs
http://localhost:8000/docs
```

### Adding a New Connector

1. Create `app/connectors/new_source_connector.py`
2. Implement `async def fetch_<source>_signals(company_name: str) -> list[SourceSignal]`
3. Import in `app/services/company_aggregator.py`
4. Add to `fetch_all_signals()` task list
5. Add to scoring algorithm if needed

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check cache
cached = await cache_service.get_cached_company("xyz training")
print(cached)

# Check database
db_record = await db_service.get_company_by_canonical_name("xyz training")
print(db_record)
```

## Scoring Algorithm Details

### Formula

```
base_score = 50.0

# Sentiment contribution (±25)
sentiment_ratio = (positive_signals - negative_signals) / total_signals
base_score += sentiment_ratio * 25

# Platform ratings contribution (0-25)
if platform_ratings_exist:
    avg_rating = mean(glassdoor_rating, ambitionbox_rating, ...)
    base_score += (avg_rating / 5.0) * 25

# Signal volume penalty
if signal_count == 0:
    base_score = 20.0  # Low confidence
elif signal_count < 3:
    base_score *= 0.9  # 10% penalty

# Red flag penalties (automatic flags added, no score penalty)
# - no_linkedin_page
# - no_glassdoor_presence
# - no_website_provided
# - course_marketed_as_internship
# - hidden_fees_indicators

# Final: clamp to 0-100
score = max(0, min(100, base_score))
```

### Risk Determination

```
if critical_flags_present:
    risk = "high"
elif score >= 75:
    risk = "low"
elif score >= 50:
    risk = "medium"
elif score >= 25:
    risk = "high"
else:
    risk = "unknown" if signal_count > 0 else "high"
```

## Database Schema (for implementation)

### PostgreSQL

```sql
CREATE TABLE companies (
    canonical_name VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    website VARCHAR(255),
    authenticityScore FLOAT,
    scamRisk VARCHAR(20),
    companyType VARCHAR(50),
    flags TEXT[],  -- JSON array
    sources TEXT,  -- JSON array
    lastCheckedAt TIMESTAMP WITH TIME ZONE
);
```

### Firestore

```
Collection: companies
Document ID: {canonical_name}
Fields:
  - name: string
  - website: string
  - authenticityScore: number
  - scamRisk: string
  - companyType: string
  - flags: array
  - sources: array
  - lastCheckedAt: timestamp
```

## Environment Variables Quick Ref

```bash
# Required
REDIS_URL=redis://...

# Optional but recommended
DATABASE_URL=postgresql://...
# OR
FIRESTORE_PROJECT_ID=...
FIRESTORE_CREDENTIALS_PATH=...

# For Reddit (optional)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...

# Customization
DEBUG=False
CORS_ORIGINS=["http://localhost:3000"]
HTTP_TIMEOUT_SECONDS=10
CACHE_TTL_SECONDS=86400
```

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot find module 'redis'` | Redis library not installed | `pip install redis` |
| `Connection refused` | Redis not running | Start Redis server or check URL |
| `403 Forbidden` from Glassdoor | Bot detection | Check User-Agent, add delays |
| `Empty response from connector` | API credentials missing | Check settings in .env |
| `Stale cache returned` | TTL not working | Verify Redis is running |

## Testing Checklist

- [ ] Redis cache is working
- [ ] Database (PostgreSQL or Firestore) is configured
- [ ] At least one connector (Reddit or Glassdoor) has credentials
- [ ] API health check returns 200: `GET /api/health`
- [ ] Can POST to check-company endpoint
- [ ] Response includes authenticityScore and flags
- [ ] CORS headers present for frontend
- [ ] Error handling works (graceful degradation if connector fails)

## Performance Targets

- **Cache hit**: < 10ms
- **Database query**: < 50ms
- **Parallel connectors (5 sources)**: < 15 seconds (slowest connector)
- **Full analysis (no cache)**: < 20 seconds
- **API response time**: < 50ms (includes network)

---

**Questions?** Check `README.md` or `IMPLEMENTATION_COMPLETE.md` for detailed docs.
