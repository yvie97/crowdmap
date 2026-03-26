# Backend

Campus occupancy backend built with FastAPI. Receives people-count data from the CV module, stores it, and serves it to the frontend via REST API and WebSocket.

---

## Project Structure

```
backend/
├── main.py       # FastAPI app: REST API endpoints + WebSocket
├── db.py         # SQLite setup: schema, insert, query
├── cache.py      # Redis helpers: read/write current occupancy
├── ingest.py     # Background task: polls CV server every second
└── venv/         # Python virtual environment (not committed)
```

---

## Data Flow

```
CV Server (port 8001)
        │
        │  every second: [{"area_id": ..., "count": ...}, ...]
        ▼
   ingest.py  ──────────────────────────────────────────┐
        │                                               │
        │ write latest count (overwrite)       every minute: snapshot
        ▼                                               ▼
      Redis                                          SQLite
  (current data)                               (historical records)
        │                                               │
        ▼                                               ▼
  GET /api/areas                         GET /api/areas/{id}/history
  GET /api/recommend                             (trend chart)
  WS  /ws/density ◄── pushed automatically on every new reading
        │
        ▼
    Frontend
```

---

## Prerequisites

**1. Install Redis (the database service) via Homebrew:**
```bash
brew install redis
brew services start redis
```

**2. Python 3.11+**

**3. Kone's CV server running on port 8001**

---

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Run

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/areas` | Current occupancy for all 4 areas |
| GET | `/api/areas/{area_id}/history?hours=24` | Historical trend for one area |
| GET | `/api/recommend` | All areas sorted by occupancy (least crowded first) |
| WS  | `/ws/density` | Real-time push updates |

---

## Area IDs

| ID | Name |
|----|------|
| `area_225_2f_1` | North Corridor |
| `area_225_2f_2` | Northeast Open Area |
| `area_225_2f_3` | Northwest Open Area |
| `area_225_2f_4` | East Corridor |
