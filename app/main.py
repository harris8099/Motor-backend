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
        # Create fault_logs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fault_logs (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                fault_type VARCHAR(32) NOT NULL,
                severity VARCHAR(16) NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
                status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cleared_pending_close', 'resolved')),
                message TEXT,
                detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                cleared_at TIMESTAMPTZ,
                resolved_at TIMESTAMPTZ,
                resolved_by VARCHAR(128),
                root_cause VARCHAR(32),
                actions_taken TEXT,
                parts_replaced TEXT,
                resolution_notes TEXT,
                sensor_reading_id INTEGER
            )
        """))
        await conn.execute(text("""
            ALTER TABLE fault_logs
            ADD COLUMN IF NOT EXISTS cleared_at TIMESTAMPTZ
        """))
        await conn.execute(text("""
            ALTER TABLE fault_logs
            ALTER COLUMN status TYPE VARCHAR(32)
        """))
        await conn.execute(text("""
            ALTER TABLE fault_logs
            DROP CONSTRAINT IF EXISTS fault_logs_status_check
        """))
        await conn.execute(text("""
            ALTER TABLE fault_logs
            ADD CONSTRAINT fault_logs_status_check
            CHECK (status IN ('active', 'cleared_pending_close', 'resolved'))
        """))
        # Create indexes separately
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_fault_logs_device_active 
            ON fault_logs(device_id, status) WHERE status = 'active'
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_fault_logs_detected_at 
            ON fault_logs(detected_at DESC)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_fault_logs_severity 
            ON fault_logs(severity) WHERE status = 'active'
        """))
        # Create commands table for remote device commands
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS commands (
                id          SERIAL PRIMARY KEY,
                device_id   VARCHAR(64) NOT NULL,
                command     VARCHAR(32) NOT NULL,
                payload     JSONB,
                status      VARCHAR(16) NOT NULL DEFAULT 'pending',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                acked_at    TIMESTAMPTZ
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_commands_device_pending
            ON commands(device_id, status, created_at)
        """))

@app.get("/health")
async def health():
    return {"status": "ok"}
