"""
pythoncv.py — 视频接入层 + FastAPI 服务
★ 加新摄像头只需在 SOURCES 里新增一行，其余代码不动 ★
"""
import threading
import cv2
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from detector import detect_people   # ← 模型逻辑全部在 detector.py

# ══════════════════════════════════════════════════════════════
# ★ 唯一需要修改的地方：视频源配置表 ★
#
# 每个摄像头/视频是一行字典：
#   area_id — 必须和 db.py 里的 AREA_IDS 一致
#   video   — 文件路径，或摄像头索引（0, 1, 2...）
#   roi     — (x_min, y_min, x_max, y_max)，只统计框内的人
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
        "video":   "demo_video03.MOV",
        "roi":     (0, 0, 6000, 6000),
     },
        {
        "area_id": "area_225_2f_4",
        "video":   "demo_video04.MOV",
        "roi":     (0, 000, 6000, 6000),
    }
        # {
    #     "area_id": "area_225_2f_4",
    #     "video":   0,           # 直接接实体摄像头用索引
    #     "roi":     (100, 100, 1820, 980),
    # },
]
# ══════════════════════════════════════════════════════════════


# ── 每个 area_id 对应一个共享状态 dict ───────────────────────
# 结构：{ area_id: {"count": int, "latest_frame": bytes | None} }
_state: dict[str, dict] = {
    src["area_id"]: {"count": 0, "latest_frame": None}
    for src in SOURCES
}
_state_lock = threading.Lock()


def _run_source(src: dict):
    """后台线程：持续读取一路视频，检测人数，更新 _state。"""
    area_id = src["area_id"]
    roi     = src["roi"]
    video   = src["video"]

    cap = cv2.VideoCapture(video)

    while True:
        ret, frame = cap.read()
        if not ret:                        # 视频播完 → 循环
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        count, annotated = detect_people(frame, roi)

        ret2, buf = cv2.imencode(".jpg", annotated)
        jpeg = buf.tobytes() if ret2 else None

        with _state_lock:
            _state[area_id]["count"]        = count
            _state[area_id]["latest_frame"] = jpeg


def _frame_generator(area_id: str):
    """把指定摄像头的最新帧包装成 MJPEG 流。"""
    while True:
        with _state_lock:
            jpeg = _state[area_id]["latest_frame"]
        if jpeg:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")


# ── FastAPI 应用 ─────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/video_feed/{area_id}")
def video_feed(area_id: str):
    """MJPEG 视频流，按 area_id 区分。例：/video_feed/area_225_2f_1"""
    if area_id not in _state:
        return {"error": "area_id not found"}
    return StreamingResponse(
        _frame_generator(area_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/current_count")
def get_current_count():
    """返回所有摄像头的最新人数，格式与 ingest.py 兼容。"""
    with _state_lock:
        return [
            {"area_id": aid, "count": data["count"]}
            for aid, data in _state.items()
        ]


# ── 启动：为每路视频起一个后台线程 ──────────────────────────
if __name__ == "__main__":
    for src in SOURCES:
        t = threading.Thread(target=_run_source, args=(src,), daemon=True)
        t.start()
        print(f"[pythoncv] Started source: {src['area_id']} ← {src['video']}")

    uvicorn.run(app, host="0.0.0.0", port=8001)