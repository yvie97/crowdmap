FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn

COPY mock_stream.py .

EXPOSE 8001

CMD ["python3", "mock_stream.py"]
