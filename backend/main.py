import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, query_history, AREA_IDS, AREA_META
from cache import get_current
from ingest import poll_and_store


def get_level(count: int, capacity: int) -> str:
    ratio = count / capacity
    if ratio <= 0.33:
        return "low"
    elif ratio <= 0.66:
        return "medium"
    return "high"


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


async def on_cv_update(areas: list[dict]):
    """Called by ingest.py after each successful poll. Broadcasts to all WebSocket clients."""
    now = int(time.time())
    payload = {
        "areas": [
            {
                "area_id": item["area_id"],
                "count": item["count"],
                "level": get_level(item["count"], AREA_META[item["area_id"]]["capacity"]),
            }
            for item in areas
            if item["area_id"] in AREA_META
        ],
        "timestamp": now,
    }
    await manager.broadcast(payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database ready.")
    asyncio.create_task(poll_and_store(on_update=on_cv_update))
    print("CV polling started.")
    yield


app = FastAPI(title="Campus Occupancy API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/areas")
def get_areas():
    results = []
    for area_id in AREA_IDS:
        meta = AREA_META[area_id]
        cached = get_current(area_id)
        count = cached["count"] if cached else 0
        timestamp = cached["timestamp"] if cached else int(time.time())
        results.append({
            "area_id": area_id,
            "name": meta["name"],
            "count": count,
            "capacity": meta["capacity"],
            "level": get_level(count, meta["capacity"]),
            "timestamp": timestamp,
        })
    return results


@app.get("/api/areas/{area_id}/history")
def get_history(area_id: str, hours: int = 24):
    if area_id not in AREA_IDS:
        raise HTTPException(status_code=404, detail="Area not found")
    since = int(time.time()) - hours * 3600
    return query_history(area_id, since)


@app.get("/api/recommend")
def recommend():
    results = []
    for area_id in AREA_IDS:
        meta = AREA_META[area_id]
        cached = get_current(area_id)
        count = cached["count"] if cached else 0
        results.append({
            "area_id": area_id,
            "name": meta["name"],
            "count": count,
            "capacity": meta["capacity"],
            "level": get_level(count, meta["capacity"]),
        })
    return sorted(results, key=lambda x: x["count"])


@app.websocket("/ws/density")
async def websocket_density(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)
