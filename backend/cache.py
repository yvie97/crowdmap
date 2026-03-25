import json
import redis

# Connect to local Redis instance
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def _key(area_id: str) -> str:
    return f"area:{area_id}:current"


def set_current(area_id: str, count: int, timestamp: int):
    """Write the latest count for an area into Redis."""
    r.set(_key(area_id), json.dumps({"count": count, "timestamp": timestamp}))


def get_current(area_id: str) -> dict | None:
    """Read the latest count for an area from Redis. Returns None if not set."""
    raw = r.get(_key(area_id))
    if raw is None:
        return None
    return json.loads(raw)


def get_all_current(area_ids: list[str]) -> dict[str, dict | None]:
    """Read latest counts for all areas at once."""
    return {area_id: get_current(area_id) for area_id in area_ids}
