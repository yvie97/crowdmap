"""
"""
import threading
import cv2
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from detector import detect_people   

# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
SOURCES = [
    {
        "area_id": "area_225_2f_1",
        "video":   "demo_video01.MOV",
        "roi":     (0, 0, 6000, 6000),
    },
        {
        "area_id": "area_225_2f_2",
        "video":   "demo_video02.MOV",
        "roi":     (0, 0, 6000, 6000),
     },
        {
        "area_id": "area_225_2f_3",
        "video":   "demo_video02.MOV",
        "roi":     (0, 0, 6000, 6000),
     },
        {
        "area_id": "area_225_2f_4",
        # "video":   "demo_video04.MOV",
        "video":   0,           
        "roi":     (0, 000, 6000, 6000),
    }
    # {
    #     "area_id": "area_225_2f_4",
    #     "video":   0,          
    #     "roi":     (100, 100, 1820, 980),
    # },
]
# ══════════════════════════════════════════════════════════════



# ：{ area_id: {"count": int, "latest_frame": bytes | None} }
_state: dict[str, dict] = {
    src["area_id"]: {"count": 0, "latest_frame": None}
    for src in SOURCES
}
_state_lock = threading.Lock()


def _run_source(src: dict):

    area_id = src["area_id"]
    roi     = src["roi"]
    video   = src["video"]

    cap = cv2.VideoCapture(video)

    while True:
        ret, frame = cap.read()
        if not ret:                        
            if isinstance(video, int):
                print(f"[{area_id}] Camera read failed, retrying...")
                cap.release()
                cap = cv2.VideoCapture(video)
                continue
            else:
               
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

        count, annotated = detect_people(frame, roi)

        ret2, buf = cv2.imencode(".jpg", annotated)
        jpeg = buf.tobytes() if ret2 else None

        with _state_lock:
            _state[area_id]["count"]        = count
            _state[area_id]["latest_frame"] = jpeg


def _frame_generator(area_id: str):
    while True:
        with _state_lock:
            jpeg = _state[area_id]["latest_frame"]
        if jpeg:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")


# ── ─────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/video_feed/{area_id}")
def video_feed(area_id: str):
    if area_id not in _state:
        return {"error": "area_id not found"}
    return StreamingResponse(
        _frame_generator(area_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/current_count")
def get_current_count():
    with _state_lock:
        return [
            {"area_id": aid, "count": data["count"]}
            for aid, data in _state.items()
        ]


if __name__ == "__main__":
    for src in SOURCES:
        t = threading.Thread(target=_run_source, args=(src,), daemon=True)
        t.start()
        print(f"[pythoncv] Started source: {src['area_id']} ← {src['video']}")

    uvicorn.run(app, host="0.0.0.0", port=8001)