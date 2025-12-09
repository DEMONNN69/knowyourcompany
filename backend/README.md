# Know Your Company - Backend

Company Authenticity Checker backend built with FastAPI. Aggregates signals from multiple external sources to assess company legitimacy.

## Features

- **Multi-source aggregation**: Reddit, X/Twitter, Glassdoor, AmbitionBox, LinkedIn
- **Rule-based scoring**: No expensive LLMs, uses keyword analysis and heuristics
- **Caching**: Redis/Upstash integration for fast repeated queries
- **Persistence**: Firestore or PostgreSQL support
- **Async/Concurrent**: Parallel fetching from multiple sources
- **Type-safe**: Full Pydantic validation and type hints
- **Production-ready**: Proper error handling, logging, and configuration

## Tech Stack

- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation with type hints
- **httpx** - Async HTTP client for external APIs
- **Redis** - Caching layer
- **BeautifulSoup4** - HTML parsing for web scraping
- **Python 3.11+** - Async/await support

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py           # API endpoints
│   ├── core/
│   │   └── config.py            # Settings from environment
│   ├── models/
│   │   └── company.py           # Pydantic models
│   ├── services/
│   │   ├── cache.py             # Redis caching service
│   │   ├── repository.py        # Database persistence (Firestore/Postgres)
│   │   ├── scoring.py           # Rule-based scoring engine
│   │   └── company_aggregator.py # Orchestrates data fetching
│   └── connectors/
│       ├── reddit_connector.py
│       ├── x_connector.py
│       ├── glassdoor_connector.py
│       ├── ambitionbox_connector.py
│       └── linkedin_connector.py
├── main.py                      # FastAPI app entry point
├── pyproject.toml              # Dependencies
├── .env.example                # Environment variables template
└── README.md
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Redis server (for caching)
- PostgreSQL or Firestore (for persistence)

### Setup

1. **Clone and navigate to backend**:
   ```bash
   cd backend
   ```

2. **Install dependencies** (using uv or pip):
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or with pip
   pip install -e .
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

4. **Run development server**:
   ```bash
   # Using uv
   uv run python main.py
   
   # Or direct python
   python main.py
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Check Company Authenticity

**POST** `/api/check-company`

Request:
```json
{
  "name": "XYZ Training Academy",
  "website": "https://xyztraining.com",
  "country": "India",
  "category": "training"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "name": "XYZ Training Academy",
    "canonical_name": "xyz training academy",
    "website": "https://xyztraining.com",
    "authenticityScore": 42.5,
    "scamRisk": "high",
    "companyType": "training",
    "flags": ["course_marketed_as_internship", "no_linkedin_page"],
    "sources": [...],
    "lastCheckedAt": "2025-12-09T10:00:00Z"
  },
  "message": "Company analysis completed successfully"
}
```

### Get Company Record

**GET** `/api/company/{canonical_name}`

Retrieve a previously checked company from cache/database.

### Refresh Company Data

**POST** `/api/company/{canonical_name}/refresh`

Force refresh a company's data, bypassing cache.

### Health Check

**GET** `/api/health`

Returns service health status.

## Scoring Algorithm

The authenticity score (0-100) is computed using:

1. **Sentiment Analysis**: Keyword matching in external signals
   - Positive keywords: "good learning", "helpful", "got stipend", etc.
   - Negative keywords: "scam", "fraud", "unpaid", "pay to", etc.

2. **Platform Ratings**: Average ratings from Glassdoor and AmbitionBox

3. **Signal Volume**: Penalizes companies with too few external signals

4. **Red Flags**:
   - No LinkedIn presence
   - No Glassdoor reviews
   - Course marketed as internship
   - Hidden fees indicators

5. **Company Type Inference**: Detects training, edtech, staffing, or IT services

### Scam Risk Levels

- **Low**: Score ≥ 75
- **Medium**: Score 50-74
- **High**: Score < 50 or critical flags present
- **Unknown**: Insufficient data

## Configuration

Create a `.env` file with the following variables:

```env
# App
DEBUG=False
APP_NAME="Know Your Company"
APP_VERSION="0.1.0"

# Server
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Redis (required for caching)
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=86400

# Database (choose one)
DATABASE_URL=postgresql://user:pass@localhost/kyco
# OR
FIRESTORE_PROJECT_ID=your-project-id
FIRESTORE_CREDENTIALS_PATH=/path/to/credentials.json

# External APIs
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
HTTP_TIMEOUT_SECONDS=10
```

## Development

### Implement Missing Connectors

Several connectors are stubbed and ready for implementation:

1. **Reddit Connector**: Use official Reddit API with authentication
2. **X/Twitter Connector**: Implement Twikit integration
3. **Glassdoor Connector**: Refine Apollo state extraction based on actual page structure
4. **AmbitionBox Connector**: Update CSS selectors based on current page layout
5. **LinkedIn Connector**: Implement Selenium-based company profile detection

### Add Database Support

The repository layer supports three backends:

1. **In-Memory** (default for development)
2. **Firestore** (TODO: Implement Firebase Admin SDK integration)
3. **PostgreSQL** (TODO: Implement SQLAlchemy async ORM)

## Error Handling

The API gracefully handles connector failures:

- If a connector fails, others continue executing
- Partial results are returned with available signals
- Scores are adjusted based on signal volume
- Detailed errors are logged for debugging

## Performance Considerations

- **Caching**: Redis caches results for 24 hours
- **Parallel Fetching**: All connectors execute concurrently
- **Async I/O**: Non-blocking external HTTP calls
- **Rate Limiting**: Respects API rate limits with timeouts

## Contributing

When adding new features:

1. Add unit tests in `tests/`
2. Follow type hints throughout
3. Update docstrings with examples
4. Log important operations
5. Handle exceptions gracefully

## License

Proprietary - Know Your Company Platform

## Support

For issues or questions, please contact the development team.
