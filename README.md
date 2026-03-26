 python3 -m venv venv

 source venv/bin/activate

pip install opencv-python ultralytics fastapi uvicorn redis httpx


brew install redis // if needed


// if occupied: kill -9 $(lsof -ti :8001)

run the program:

brew services start redis 

python3 pythoncv.py 

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

npm install
npm start


//
http://localhost:8001/video_feed 看看视频流画面

