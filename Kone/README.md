## 🛠️ 安装与运行指南 (Installation & Setup)

为了确保每个人都能顺利运行本项目，避免不同电脑上的环境冲突，我们强烈建议使用 Python 的**虚拟环境**来配置项目。请按照以下详细步骤操作：

### 第一步：创建并激活虚拟环境 (Virtual Environment)

1. **打开终端 (Terminal / Command Prompt):** 进入本项目的根目录（即 `pythoncv.py` 所在的文件夹）。

2. **创建虚拟环境:**
   在终端中输入以下命令，这会在当前文件夹下生成一个名为 `venv` 的隔离环境：
   * **Mac / Linux:** 
     ```bash
     python3 -m venv venv
     ```
   * **Windows:** 
     ```bash
     python -m venv venv
     ```

3. **激活虚拟环境 (非常重要❗️):**
   只有激活后，你安装的库才会被放在这个隔离环境中。根据你的系统运行相应的命令：
   * **Mac / Linux:** 
     ```bash
     source venv/bin/activate
     ```
   * **Windows:** 
     ```bash
     venv\Scripts\activate
     ```
   > ✅ **成功标志：** 激活成功后，你的命令行提示符最前面会出现 `(venv)` 字样。

### 第二步：安装必备依赖库 (Install Dependencies)

在确保虚拟环境**已激活**（终端带有 `(venv)` 标志）的情况下，我们需要安装计算机视觉和后端服务器相关的库。

在终端中复制并运行以下命令，一次性安装所有必备库：
```bash
pip install opencv-python ultralytics fastapi uvicorn
```
*库说明：*
* `opencv-python`: 用于读取视频帧和绘制画面。
* `ultralytics`: YOLOv8 官方库，用于核心的人数目标检测。
* `fastapi` & `uvicorn`: 用于搭建轻量级后端，将视频流和数据发送给前端。

### 第三步：运行后端与前端 (Run the Application)

1. **准备视频文件:**
   请确保你的测试视频文件（例如代码中指定的 `demo_video01.MOV`）已经放在了与 `pythoncv.py` **同一个文件夹**内。

2. **启动 Python 后端:**
   在终端中（保持虚拟环境激活状态）运行以下命令：
   ```bash
   python3 pythoncv.py
   ```
   > ⏳ **注意：** 第一次运行此命令时，系统会自动下载 YOLOv8 的轻量级模型文件 (`yolov8n.pt`)，可能需要几秒到一分钟的时间，请耐心等待。当终端出现类似 `Uvicorn running on http://0.0.0.0:8000` 的提示时，说明后端已成功启动！

3. **打开前端展示界面:**
   后端保持运行不要关闭。打开你的文件管理器，找到项目文件夹中的 `Frontend_index.html` 文件，**直接双击**用浏览器打开。
   
   你现在应该能看到实时的监控画面、当前识别到的人数，以及随时间变化的历史人数趋势图了！🎉