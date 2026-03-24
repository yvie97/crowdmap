import cv2
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 1. 初始化 FastAPI 应用
app = FastAPI()

# 2. 允许跨域请求（非常重要：不然你的本地 HTML 网页会被浏览器拦截，拿不到数据）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载模型
model = YOLO("yolov8n.pt")

# 全局变量：用于在视频流和 API 之间共享最新的人数
current_people_count = 0

def generate_frames():
    global current_people_count
    cap = cv2.VideoCapture(0)
    ROI = (200, 150, 500, 400)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        people_count = 0

        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls == 0 and conf > 0.4:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                if ROI[0] < cx < ROI[2] and ROI[1] < cy < ROI[3]:
                    people_count += 1
                    color = (0, 255, 0)
                else:
                    color = (0, 0, 255)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.circle(frame, (cx, cy), 5, color, -1)

        cv2.rectangle(frame, (ROI[0], ROI[1]), (ROI[2], ROI[3]), (255, 0, 0), 2)
        cv2.putText(frame, f"People in ROI: {people_count}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 3. 更新全局变量，把最新的人数存起来
        current_people_count = people_count

        # 4. 把 OpenCV 的图像转换为网络传输支持的 JPEG 格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # 5. 按照 MJPEG 流的格式不断生成数据
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# 接口一：前端用 <img src="..."> 来接这个视频流
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# 接口二：前端 JavaScript 用 fetch 来获取最新人数
@app.get("/api/current_count")
def get_current_count():
    return {"count": current_people_count}

if __name__ == "__main__":
    # 启动服务器，运行在本地的 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)