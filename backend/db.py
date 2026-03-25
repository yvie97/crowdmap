import sqlite3

DB_PATH = "occupancy.db"

AREA_IDS = [
    "area_225_2f_1",
    "area_225_2f_2",
    "area_225_2f_3",
    "area_225_2f_4",
]

AREA_META = {
    "area_225_2f_1": {"name": "Area 1", "capacity": 20},
    "area_225_2f_2": {"name": "Area 2", "capacity": 20},
    "area_225_2f_3": {"name": "Area 3", "capacity": 20},
    "area_225_2f_4": {"name": "Area 4", "capacity": 20},
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS occupancy_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id     TEXT    NOT NULL,
            count       INTEGER NOT NULL,
            recorded_at INTEGER NOT NULL
        )
    """)

    # Index for fast queries by area + time range
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_area_recorded
        ON occupancy_history (area_id, recorded_at)
    """)

    conn.commit()
    conn.close()


def insert_record(area_id: str, count: int, recorded_at: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO occupancy_history (area_id, count, recorded_at) VALUES (?, ?, ?)",
        (area_id, count, recorded_at),
    )
    conn.commit()
    conn.close()


def query_history(area_id: str, since: int) -> list[dict]:
    """Return records for area_id where recorded_at >= since."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT area_id, count, recorded_at FROM occupancy_history "
        "WHERE area_id = ? AND recorded_at >= ? ORDER BY recorded_at ASC",
        (area_id, since),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"area_id": r[0], "count": r[1], "recorded_at": r[2]} for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
