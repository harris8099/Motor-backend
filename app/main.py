from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import data, faults, predictions, forecast
from app.database import engine, Base

app = FastAPI(title="ESP32 Motor Monitor API")

# Configure CORS for frontend
# In production, replace with your actual Vercel URL
# For now, allowing all origins (restrict in production for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(faults.router)
app.include_router(predictions.router)
app.include_router(forecast.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
