from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.routers import data, faults, predictions, forecast, devices, auth
from app.database import engine, Base, settings

app = FastAPI(title="ESP32 Motor Monitor API")

# Configure CORS for frontend
# In production, replace with your actual Vercel URL
# For now, allowing all origins (restrict in production for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url] if settings.frontend_url != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(faults.router)
app.include_router(predictions.router)
app.include_router(forecast.router)
app.include_router(devices.router)
app.include_router(auth.router)

@app.on_event("startup")
async def ensure_schema_columns():
    async with engine.begin() as conn:
        # Create users table if not exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # Add last_ai_analysis_at to devices if not exists
        await conn.execute(text("""
            ALTER TABLE devices
            ADD COLUMN IF NOT EXISTS last_ai_analysis_at TIMESTAMPTZ
        """))

@app.get("/health")
async def health():
    return {"status": "ok"}
