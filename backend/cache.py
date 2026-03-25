import json
import redis

# Connect to the local Redis instance (started via: brew services start redis)
# Redis stores the latest occupancy count for each area in memory for fast reads
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def _key(area_id: str) -> str:
    """Returns the Redis key for a given area, e.g. 'area:area_225_2f_1:current'"""
    return f"area:{area_id}:current"


def set_current(area_id: str, count: int, timestamp: int):
    """Overwrite the latest count for an area in Redis.
    Called every second when new data arrives from Kone's CV server.
    Old value is replaced - Redis always holds only the most recent reading.
    """
    r.set(_key(area_id), json.dumps({"count": count, "timestamp": timestamp}))


def get_current(area_id: str) -> dict | None:
    """Read the latest count for an area from Redis.
    Returns None if no data has arrived yet for this area.
    """
    raw = r.get(_key(area_id))
    if raw is None:
        return None
    return json.loads(raw)


def get_all_current(area_ids: list[str]) -> dict[str, dict | None]:
    """Read latest counts for all areas at once."""
    return {area_id: get_current(area_id) for area_id in area_ids}
