# Relocation & Evacuation Decision Support System — Backend MVP

A Smart Multi-Hazard Relocation and Evacuation Decision Support System backend, built for hackathon demo. Uses mock/seed data with a transparent weighted decision pipeline.

## Quick Start

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys (or leave defaults for demo)

# 5. Run the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The server starts at `http://127.0.0.1:8000`. On first run, it automatically creates a SQLite database and loads seed data.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `APP_API_KEY` | Yes | Internal API key for authentication (sent as `X-API-Key` header) |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins (default: `http://localhost:5173,http://localhost:3000`) |
| `DEFAULT_RATE_LIMIT` | No | Global rate limit (default: `30/minute`) |
| `EXPENSIVE_ROUTE_RATE_LIMIT` | No | Rate limit for expensive endpoints (default: `10/minute`) |
| `MAX_GEMINI_CALLS_PER_MINUTE` | No | Hard cap on Gemini API calls (default: `5`) |
| `MAX_WEATHER_CALLS_PER_MINUTE` | No | Hard cap on weather API calls (default: `10`) |
| `GEMINI_API_KEY` | No | Google Gemini API key (optional — degrades gracefully without it) |
| `WEATHER_API_KEY` | No | Weather API key (optional — uses seed data without it) |
| `DATABASE_URL` | No | SQLite database path (default: `sqlite:///./relocation.db`) |
| `CACHE_TTL_SECONDS` | No | Cache TTL for API responses (default: `600`) |

## API Endpoints

### Health Check (no auth required)

```bash
curl http://127.0.0.1:8000/health
```

### Villages

```bash
# List all villages
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/villages

# Filter by state
curl -H "X-API-Key: YOUR_KEY" "http://127.0.0.1:8000/villages?state=Assam"

# Get single village
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/villages/V001
```

### Risk Assessment

```bash
curl -X POST http://127.0.0.1:8000/risk/assess \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"village_id": "V001"}'
```

### Generate Evacuation Plan (Main Endpoint)

```bash
curl -X POST http://127.0.0.1:8000/relocation/generate-plan \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "village_id": "V001",
    "search_radius_km": 120.0,
    "include_ai_summary": false
  }'
```

**With custom weights:**

```bash
curl -X POST http://127.0.0.1:8000/relocation/generate-plan \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "village_id": "V001",
    "search_radius_km": 120.0,
    "weights": {
      "safety": 0.30,
      "capacity": 0.20,
      "route": 0.15,
      "healthcare": 0.15,
      "water": 0.10,
      "vulnerability_fit": 0.05,
      "distance": 0.05
    },
    "include_ai_summary": false
  }'
```

### What-If Simulation

```bash
curl -X POST http://127.0.0.1:8000/simulation/run \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "village_id": "V001",
    "overrides": {
      "rainfall_multiplier": 2.0,
      "occupancy_percent": 0.8,
      "road_accessibility_percent": 0.6
    }
  }'
```

### Dashboard Overview

```bash
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:8000/dashboard/overview
```

## Architecture

```
Request → API Key Check → Rate Limiter → Router → Services → Response
                                    ↓
                              SQLite DB
```

### Decision Pipeline (9 Steps)

1. **Hazard Risk Engine** — Weighted formula: rainfall + river proximity + elevation + historical frequency
2. **Vulnerability Engine** — Population demographics: children + elderly + special assistance
3. **Candidate Engine** — Haversine search within radius
4. **Filtering Engine** — Hard constraints: hazard threshold, blocked routes, zero capacity
5. **Capacity Engine** — Available beds = total - current occupancy
6. **Route Engine** — Safety scoring with flood/landslide penalties
7. **Optimization Engine** — Multi-criteria weighted scoring (7 factors)
8. **Allocation Engine** — Greedy bin-packing across ranked destinations
9. **Explainability Engine** — Human-readable reasons + AI summary (optional)

### Security Features

- **API Key Authentication** — Every protected endpoint requires `X-API-Key` header
- **Rate Limiting** — 30/min global, 10/min for expensive endpoints
- **Outbound API Protection** — TTL cache + hard call caps for Gemini/weather APIs
- **Graceful Degradation** — Falls back to rule-based summaries if AI unavailable
- **CORS** — Explicit allowed origins from `.env`, not `*`
- **Input Validation** — Pydantic bounds on lat/lng, population, radius

## Seed Data

The demo includes 13 villages across Assam and Bihar with realistic locations:

| Village | State | Risk | Notes |
|---|---|---|---|
| Dhemaji Town | Assam | HIGH | Source village |
| Gogamukh | Assam | MEDIUM | Good candidate |
| Jonai | Assam | LOW | No healthcare |
| Majuli Island | Assam | EXTREME | Rejected |
| North Lakhimpur | Assam | LOW | Best candidate |
| Jorhat Town | Assam | LOW | Best infrastructure |
| Sivasagar Town | Assam | LOW | Route blocked |

## Tech Stack

- **FastAPI** — Async web framework
- **SQLModel** — SQLAlchemy + Pydantic integration
- **SQLite** — File-based database (no PostgreSQL required)
- **slowapi** — Rate limiting
- **cachetools** — In-memory TTL cache
- **geopy/haversine** — Distance calculations
- **httpx** — Async HTTP client for external APIs

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, routers, middleware
│   ├── config.py            # Environment variable loading
│   ├── security.py          # API key auth, rate limiter
│   ├── database.py          # SQLite setup, seed data loading
│   ├── models/
│   │   ├── db_models.py     # SQLModel table definitions
│   │   └── schemas.py       # Pydantic request/response models
│   ├── data/
│   │   ├── seed_villages.json
│   │   ├── seed_shelters.json
│   │   └── seed_routes.json
│   ├── services/            # Business logic engines
│   └── routers/             # API endpoint handlers
├── .env.example
├── requirements.txt
└── README.md
```

## Troubleshooting

**"APP_API_KEY is still the placeholder value"**
→ Set a real key in `.env` before production use.

**Rate limit exceeded (429)**
→ Wait for the `Retry-After` period, or reduce request frequency.

**Gemini/Weather API errors**
→ System degrades gracefully — rule-based summaries used instead.

**Database not found**
→ Auto-created on first startup with seed data.

## License

Internal hackathon project.
