"""
mock_stream.py — Drop-in replacement for pythoncv.py when no camera is available.

Exposes the same API:
    GET /api/current_count  →  [{"area_id": "...", "count": N}, ...]

Occupancy is simulated using a time-of-day pattern (weekday university building)
plus a per-area random walk, so the frontend map stays lively.

Run:
    python3 mock_stream.py
"""

import time
import random
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Area definitions (must match backend/db.py) ───────────────────────────────

AREAS = {
    "area_225_2f_1": {"name": "North Corridor",      "capacity": 8},
    "area_225_2f_2": {"name": "Northeast Open Area", "capacity": 20},
    "area_225_2f_3": {"name": "Northwest Open Area", "capacity": 20},
    "area_225_2f_4": {"name": "East Corridor",       "capacity": 8},
}

# ── Time-of-day pattern ───────────────────────────────────────────────────────
# Keypoints: (hour_of_day, base_occupancy_ratio 0–1)
# Models a typical university building weekday.

BASE_PATTERN: list[tuple[float, float]] = [
    ( 0.0, 0.00),   # midnight      — closed
    ( 7.0, 0.00),   # 7am           — just opening
    ( 7.5, 0.40),   # opening       — people arriving
    ( 8.0, 0.75),   # morning rush
    ( 9.5, 0.52),   # mid-morning   — settled
    (12.0, 0.70),   # lunch rush
    (13.5, 0.46),   # early afternoon
    (17.0, 0.78),   # evening rush
    (19.5, 0.26),   # winding down
    (21.5, 0.05),   # almost closing
    (22.0, 0.00),   # closed
    (24.0, 0.00),   # closed
]

# Per-area tweaks so zones don't move in lockstep.
# scale: multiplier on base ratio  |  phase: hour shift (+  = peaks later)
AREA_PARAMS: dict[str, dict] = {
    "area_225_2f_1": {"scale": 0.90, "phase": -0.25},  # North Corridor:  slightly earlier
    "area_225_2f_2": {"scale": 1.00, "phase":  0.00},  # Northeast Open:  baseline
    "area_225_2f_3": {"scale": 0.85, "phase":  0.30},  # Northwest Open:  slightly later
    "area_225_2f_4": {"scale": 0.75, "phase": -0.10},  # East Corridor:   quieter overall
}

# Per-area random-walk state (persists between requests)
_noise: dict[str, float] = {area_id: 0.0 for area_id in AREAS}


def _lerp(hour: float) -> float:
    """Linearly interpolate base ratio from keypoints for the given hour."""
    for i in range(len(BASE_PATTERN) - 1):
        h0, v0 = BASE_PATTERN[i]
        h1, v1 = BASE_PATTERN[i + 1]
        if h0 <= hour < h1:
            t = (hour - h0) / (h1 - h0)
            return v0 + t * (v1 - v0)
    return BASE_PATTERN[-1][1]


def _get_count(area_id: str) -> int:
    """Return a mock occupancy count: time-of-day base + random walk noise."""
    params   = AREA_PARAMS[area_id]
    capacity = AREAS[area_id]["capacity"]

    lt   = time.localtime()
    hour = lt.tm_hour + lt.tm_min / 60.0 + lt.tm_sec / 3600.0

    # Building closed 22:00 – 07:00
    if hour >= 22.0 or hour < 7.0:
        _noise[area_id] = 0.0   # reset so noise doesn't drift while closed
        return 0

    # Shift hour per area, then interpolate base ratio
    base = _lerp((hour + params["phase"]) % 24) * params["scale"]

    # Random walk — small step each call, clamped so it never dominates
    _noise[area_id] += random.uniform(-0.04, 0.04)
    _noise[area_id]  = max(-0.12, min(0.12, _noise[area_id]))

    ratio = max(0.0, min(1.0, base + _noise[area_id]))
    return round(ratio * capacity)


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="CrowdMap Mock CV Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/current_count")
def current_count():
    """Same response format as the real pythoncv.py CV server."""
    return [{"area_id": aid, "count": _get_count(aid)} for aid in AREAS]


if __name__ == "__main__":
    print("[mock_stream] Starting on port 8001")
    print("[mock_stream] Simulating time-of-day occupancy (no camera needed)")
    uvicorn.run(app, host="0.0.0.0", port=8001)
