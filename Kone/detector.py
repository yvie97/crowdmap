"""
detector.py — YOLO模型封装层
只负责"给我一帧图像，告诉你里面有几个人"
不包含任何视频源、路径、area_id的概念
"""
import cv2
from ultralytics import YOLO

# ── 模型配置（唯一需要在这里改的地方）──────────────────────────
MODEL_PATH          = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.4
PERSON_CLASS_ID     = 0          # COCO 数据集里 0 = person
# ────────────────────────────────────────────────────────────────

# 模型只加载一次，所有摄像头共用同一个实例
_model = YOLO(MODEL_PATH)


def detect_people(
    frame,
    roi: tuple[int, int, int, int]   # (x_min, y_min, x_max, y_max)
) -> tuple[int, any]:
    """
    对单帧图像运行 YOLO 检测。

    参数：
        frame  — OpenCV BGR 图像
        roi    — 只统计中心点落在这个矩形内的人

    返回：
        (roi内人数, 标注后的frame)
    """
    results = _model(frame)
    count = 0

    for box in results[0].boxes:
        cls  = int(box.cls[0])
        conf = float(box.conf[0])

        if cls != PERSON_CLASS_ID or conf <= CONFIDENCE_THRESHOLD:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        in_roi = roi[0] < cx < roi[2] and roi[1] < cy < roi[3]
        color  = (0, 255, 0) if in_roi else (0, 0, 255)

        if in_roi:
            count += 1

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, (cx, cy), 5, color, -1)

    # 画 ROI 框 + 计数文字
    cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    cv2.putText(frame, f"People in ROI: {count}",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return count, frame
