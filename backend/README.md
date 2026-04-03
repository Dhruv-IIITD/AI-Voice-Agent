# Backend

Run the FastAPI app with:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the LiveKit worker with:

```bash
python -m app.runtime.worker dev
```
