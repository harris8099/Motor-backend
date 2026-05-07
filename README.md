# Smart Motor Backend

FastAPI backend for smart motor telemetry ingestion, prediction storage, forecasting, device management, and optional Gemini-based AI commentary.

## Features

- Receives sensor payloads from ESP32 or other device sources
- Stores telemetry, fault events, and predictions in PostgreSQL
- Serves device dashboards through REST endpoints
- Runs rule-based, ML, and advanced ML prediction pipelines
- Supports on-demand Gemini analysis through a backend-only API route

## Tech Stack

- FastAPI
- SQLAlchemy Async + asyncpg
- PostgreSQL
- NumPy / SciPy / scikit-learn
- Google GenAI SDK

## Environment

Create `.env` in this folder:

```env
DATABASE_URL=postgresql://...
API_KEY=your_shared_api_key
GEMINI_API_KEY=
GEMINI_MODE=commentary
PREDICTION_MODE=advanced
PREDICTION_DISPATCH_MODE=auto
REDIS_URL=
PREDICTION_QUEUE_NAME=prediction_jobs
```

### Environment Variables

- `DATABASE_URL`
  PostgreSQL connection string
- `API_KEY`
  Shared API key expected in the `x-api-key` header from the frontend and devices
- `GEMINI_API_KEY`
  Optional Google Gemini API key
- `GEMINI_MODE`
  `commentary`, `prediction`, or `disabled`
- `PREDICTION_MODE`
  `basic`, `ml`, or `advanced`
- `PREDICTION_DISPATCH_MODE`
  `auto`, `background`, or `redis`. `auto` uses Redis when `REDIS_URL` is set, otherwise FastAPI background tasks.
- `REDIS_URL`
  Optional Redis connection string for out-of-process prediction workers
- `PREDICTION_QUEUE_NAME`
  Optional Redis list name used for queued prediction jobs

## Install

Using the existing virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the Redis worker when traffic grows:

```powershell
python -m app.worker
```

Health check:

```text
GET /health
```

## Main Routes

- `POST /data`
  Receive telemetry payloads
- `GET /data/{device_id}`
  Fetch recent telemetry
- `GET /predictions/{device_id}`
  Fetch stored predictions
- `POST /ai/analyze/{device_id}`
  Trigger Gemini analysis for the latest reading
- `GET /devices`
  List devices

## Gemini Notes

- Gemini is called only from the backend.
- If `GEMINI_API_KEY` is empty, AI analysis returns a graceful failure message.
- If Google returns quota errors such as `429 RESOURCE_EXHAUSTED`, the backend surfaces a clearer message to the frontend.
- A valid key is not enough by itself; the linked Google project also needs usable quota.

## Database

- SQL schema setup is in `sql_setup.sql`
- The backend strips query-string SSL parameters from `DATABASE_URL` before passing the connection to `asyncpg`, then forces SSL with `connect_args={"ssl": "require"}`

## Development Notes

- CORS is currently open to all origins in `app/main.py`
- Restrict `allow_origins` before deploying publicly
- `POST /data` now dispatches prediction work through a queue abstraction. Without Redis it still uses FastAPI background tasks; with `REDIS_URL` configured it enqueues jobs for the worker process.
