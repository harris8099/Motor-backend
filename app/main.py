from fastapi import FastAPI
from app.routers import data, faults, predictions
from app.database import engine, Base

app = FastAPI(title="ESP32 Motor Monitor API")

app.include_router(data.router)
app.include_router(faults.router)
app.include_router(predictions.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
