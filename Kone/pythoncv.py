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
    
    # 🔴 修改点 1：把这里的 0 换成你的视频文件名（必须带后缀名，比如 .mp4 或 .avi）
    # 确保这个视频文件和你的 pythoncv.py 放在同一个文件夹 Kone 里
    video_path = "demo_video01.MOV" 
    cap = cv2.VideoCapture(video_path)
    
    # ⚠️ 注意：如果你的视频分辨率很大（比如 1920x1080），这个 ROI 框可能会显得很小或者位置不对
    # 你可以根据实际情况调大这些数字：(左上角x, 左上角y, 右下角x, 右下角y)
    ROI = (0, 0, 3000, 3000)

    while True:
        ret, frame = cap.read()
        
        # 🔴 修改点 2：视频循环播放逻辑
        if not ret:
            # 如果 ret 为 False，说明视频播放到最后一帧了。
            # 这里我们将视频的帧指针重新设置回第 0 帧，实现无限循环播放
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

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

        # 更新全局变量
        current_people_count = people_count

        # 图像转换为网络流格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

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