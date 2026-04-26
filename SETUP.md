
# 🚀 Project Setup Guide

Follow the steps below to run the project using **3 separate terminals**.

---

## 🧑‍💻 Terminal 1 – Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ Terminal 2 – Worker

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m app.worker dev
```

---

## 🌐 Terminal 3 – Backend (FastAPI)

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

