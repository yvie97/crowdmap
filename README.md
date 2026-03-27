# Project Setup & Running Guide

## Prerequisites

Make sure you have the following installed on your system:
- Python 3
- Node.js & npm
- Redis (`brew install redis`)

---

## Installation

### 1. Create and activate a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install opencv-python ultralytics fastapi uvicorn redis httpx
```

### 3. Install Node.js dependencies

```bash
npm install
```

---

## Running the Project

Open **three separate terminals** and follow the steps below.

> **Note:** If a port is already in use, free it with:
> ```bash
> kill -9 $(lsof -ti :8001)
> ```

---

### Terminal 1 — Redis Server

```bash
brew services start redis
```

Then, inside the `kone` directory:

```bash
source venv/bin/activate
python3 pythoncv.py
```

---

### Terminal 2 — Backend Server

Inside the `backend` directory:

```bash
source venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### Terminal 3 — Frontend

Inside the `frontend` directory:

```bash
source venv/bin/activate
npm start
```

---

## Project Structure

```
project-root/
├── kone/           # Computer vision module
│   └── pythoncv.py
├── backend/        # FastAPI backend
│   └── main.py
└── frontend/       # Frontend application
```