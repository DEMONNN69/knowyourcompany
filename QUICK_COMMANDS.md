# Quick Commands Reference

## Getting Started

### 1. Install Dependencies
```bash
cd backend
pip install -e .
# or with uv:
uv sync
```

### 2. Create Environment File
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Redis (if local)
```bash
redis-server
# or with Docker:
docker run -d -p 6379:6379 redis:latest
```

### 4. Run Server
```bash
# Development (auto-reload)
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (4 workers)
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

---

## Testing Endpoints

### Check a Company
```bash
curl -X POST http://localhost:8000/api/check-company \
  -H "Content-Type: application/json" \
  -d '{
    "name": "XYZ Training Academy",
    "website": "https://xyztraining.com",
    "country": "India",
    "category": "training"
  }'
```

### Get Cached Company
```bash
curl http://localhost:8000/api/company/xyz-training-academy
```

### Refresh Company Data
```bash
curl -X POST http://localhost:8000/api/company/xyz-training-academy/refresh
```

### Health Check
```bash
curl http://localhost:8000/api/health
```

### View API Docs
```bash
open http://localhost:8000/docs
```

---

## Development Commands

### Enable Debug Logging
```bash
export DEBUG=True
python main.py
```

### Run with Specific Port
```bash
python main.py --port 8001
```

### Check Dependencies
```bash
pip list
# or with uv:
uv pip list
```

### Update Dependencies
```bash
pip install --upgrade -e .
# or with uv:
uv sync
```

---

## Database Setup

### PostgreSQL
```bash
# Create database
createdb kyco

# In .env:
DATABASE_URL=postgresql://user:password@localhost:5432/kyco

# Connection test:
psql kyco -c "SELECT version();"
```

### Firestore
```bash
# Download credentials from Firebase Console
# In .env:
FIRESTORE_PROJECT_ID=your-project-id
FIRESTORE_CREDENTIALS_PATH=/path/to/service-account-key.json
```

---

## Redis Setup

### Local Redis
```bash
# Mac (Homebrew)
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
redis-server

# Windows (via WSL)
wsl redis-server
```

### Docker Redis
```bash
docker run -d -p 6379:6379 --name redis redis:latest

# Test connection
redis-cli ping
```

### Upstash Cloud Redis
```bash
# Get URL from Upstash dashboard
# In .env:
REDIS_URL=redis://default:password@host:port
```

---

## API Examples

### Python Requests
```python
import requests

response = requests.post(
    "http://localhost:8000/api/check-company",
    json={
        "name": "Example Corp",
        "website": "https://example.com"
    }
)

result = response.json()
print(result['data']['authenticityScore'])
print(result['data']['scamRisk'])
```

### JavaScript Fetch
```javascript
const response = await fetch('http://localhost:8000/api/check-company', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Example Corp',
    website: 'https://example.com'
  })
});

const result = await response.json();
console.log(result.data.authenticityScore);
```

### REST Client (VS Code)
```http
POST http://localhost:8000/api/check-company
Content-Type: application/json

{
  "name": "XYZ Training Academy",
  "website": "https://xyztraining.com",
  "country": "India",
  "category": "training"
}
```

---

## Debugging

### View Logs
```bash
# Server shows logs in terminal
# For persistent logs:
python main.py 2>&1 | tee server.log
```

### Check Cache
```python
from app.services.cache import get_cache_service

cache = get_cache_service()
result = await cache.get_cached_company("xyz training")
print(result)
```

### Check Database
```python
from app.services.repository import get_db_service

db = get_db_service()
result = await db.get_company_by_canonical_name("xyz training")
print(result)
```

### Test Redis Connection
```bash
redis-cli ping
# Should return: PONG

redis-cli keys "*"
# List all cached keys

redis-cli flushall
# Clear all cache (BE CAREFUL!)
```

---

## Configuration

### Change API Port
```bash
# In .env
PORT=8001

# Or command line
python main.py --port 8001
```

### Change Cache TTL
```bash
# In .env (seconds)
CACHE_TTL_SECONDS=604800  # 7 days
```

### Add CORS Origins
```bash
# In .env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173", "https://myapp.com"]
```

### Adjust Timeouts
```bash
# In .env
HTTP_TIMEOUT_SECONDS=20
MAX_CONCURRENT_REQUESTS=10
```

---

## Docker Deployment

### Build Docker Image
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run
```bash
docker build -t kyco-backend .
docker run -p 8000:8000 -e REDIS_URL=redis://... kyco-backend
```

---

## Troubleshooting

### "Cannot find module redis"
```bash
pip install redis
```

### "Connection refused" (Redis)
```bash
# Start Redis
redis-server
# Or check if running:
redis-cli ping
```

### "403 Forbidden" (Glassdoor)
```
Add delays between requests, check User-Agent rotation
```

### "Empty response from connectors"
```
Check API credentials in .env
Enable DEBUG=True for logging
```

### "Stale cache returning"
```bash
# Clear cache manually:
redis-cli flushall
# Or use refresh endpoint:
POST /api/company/{name}/refresh
```

---

## Performance Testing

### Load Testing with Apache Bench
```bash
# Install Apache Bench
brew install ab  # or apt-get

# Run test (1000 requests, 10 concurrent)
ab -n 1000 -c 10 http://localhost:8000/api/health
```

### Load Testing with Locust
```bash
pip install locust

# Create locustfile.py
# Then:
locust -f locustfile.py --host=http://localhost:8000
```

---

## Production Checklist

- [ ] Update DEBUG=False in .env
- [ ] Set strong Redis password
- [ ] Use PostgreSQL or Firestore (not in-memory)
- [ ] Configure proper CORS_ORIGINS
- [ ] Set up monitoring/logging
- [ ] Use HTTPS for external APIs
- [ ] Test all connectors work
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Test error handling

---

## Useful Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry point |
| `app/core/config.py` | Configuration settings |
| `app/models/company.py` | Data models |
| `app/api/routes.py` | API endpoints |
| `app/services/company_aggregator.py` | Main orchestrator |
| `app/services/cache.py` | Redis caching |
| `app/services/scoring.py` | Scoring logic |
| `.env` | Configuration (create from .env.example) |

---

## Help & Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alt Docs**: http://localhost:8000/redoc (ReDoc)
- **README**: See `README.md`
- **Developer Guide**: See `DEVELOPER_GUIDE.md`
- **Implementation**: See `IMPLEMENTATION_COMPLETE.md`

---

*Last Updated: December 9, 2025*
