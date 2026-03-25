import asyncio
import time

import httpx

from cache import set_current
from db import insert_record

CV_SERVER_URL = "http://localhost:8001/api/current_count"

# How often (in seconds) to poll Kone's CV server
POLL_INTERVAL = 1

# How often (in seconds) to persist Redis data to SQLite
PERSIST_INTERVAL = 60

# Tracks the last time each area was persisted to SQLite
_last_persist: dict[str, int] = {}


async def poll_and_store(on_update=None):
    """Poll Kone's CV server every second and write results to Redis."""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(CV_SERVER_URL, timeout=2)
                areas = response.json()  # expects list of {area_id, count}

                now = int(time.time())
                for item in areas:
                    area_id = item["area_id"]
                    count = item["count"]

                    # Write to Redis (always)
                    set_current(area_id, count, now)

                    # Write to SQLite once per minute per area
                    last = _last_persist.get(area_id, 0)
                    if now - last >= PERSIST_INTERVAL:
                        insert_record(area_id, count, now)
                        _last_persist[area_id] = now

                # Notify WebSocket clients
                if on_update:
                    await on_update(areas)

            except Exception as e:
                print(f"[ingest] Failed to poll CV server: {e}")

            await asyncio.sleep(POLL_INTERVAL)
