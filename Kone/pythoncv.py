import cv2
from ultralytics import YOLO

# implement YOLO
model = YOLO("yolov8n.pt")

# turn the camera on
cap = cv2.VideoCapture(0)

# define ROI (x1, y1, x2, y2)
ROI = (200, 150, 500, 400)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO检测
    results = model(frame)

    people_count = 0

    for box in results[0].boxes:

        cls = int(box.cls[0])
        conf = float(box.conf[0])

        # class 0 = person
        if cls == 0 and conf > 0.4:

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # 人的中心点
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            # if inside ROI
            if ROI[0] < cx < ROI[2] and ROI[1] < cy < ROI[3]:
                people_count += 1

                color = (0,255,0)
            else:
                color = (0,0,255)

            # draw the rectangle
            cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
            cv2.circle(frame,(cx,cy),5,color,-1)

    # draw the ROI
    cv2.rectangle(frame,(ROI[0],ROI[1]),(ROI[2],ROI[3]),(255,0,0),2)

    # show the population
    cv2.putText(frame,
                f"People in ROI: {people_count}",
                (20,50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2)

    cv2.imshow("People Counter", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()