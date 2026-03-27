"""

"""
import cv2
from ultralytics import YOLO

MODEL_PATH          = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.4
PERSON_CLASS_ID     = 0          



_model = YOLO(MODEL_PATH)


def detect_people(
    frame,
    roi: tuple[int, int, int, int]   # (x_min, y_min, x_max, y_max)
) -> tuple[int, any]:

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


    cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    cv2.putText(frame, f"People in ROI: {count}",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return count, frame
