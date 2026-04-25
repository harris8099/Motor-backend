from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from typing import List
import math

router = APIRouter()

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

def linear_regression_forecast(values: List[float], steps: int = 12) -> List[float]:
    """Simple linear regression for forecasting"""
    if len(values) < 2:
        return values * steps if values else [0] * steps
    
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    
    # Calculate slope and intercept
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return values * steps
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Forecast future values
    forecast = []
    for i in range(steps):
        forecast.append(max(0, slope * (n + i) + intercept))
    
    return forecast

@router.get("/forecast/{device_id}")
async def get_power_forecast(
    device_id: str,
    electricity_rate: float = 8.0,
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get power and energy forecast with cost prediction"""
    
    # Fetch recent power data
    result = await db.execute(text("""
        SELECT power, energy, voltage, current, ts
        FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC
        LIMIT :limit
    """), {"device_id": device_id, "limit": min(hours, 100)})
    rows = result.mappings().all()
    
    if not rows:
        return {
            "data": [],
            "forecast": {
                "power": [],
                "energy": [],
                "cost": []
            },
            "summary": {
                "avg_power": 0,
                "projected_daily_cost": 0,
                "projected_monthly_cost": 0,
                "electricity_rate": electricity_rate
            }
        }
    
    # Convert to lists for analysis
    power_values = [float(r['power']) for r in rows if r['power'] is not None]
    energy_values = [float(r['energy']) for r in rows if r['energy'] is not None]
    current_values = [float(r['current']) for r in rows if r['current'] is not None]
    
    # Calculate averages
    avg_power = sum(power_values) / len(power_values) if power_values else 0
    avg_current = sum(current_values) / len(current_values) if current_values else 0
    
    # Generate forecasts (next 24 hours)
    forecast_horizon = 24
    power_forecast = linear_regression_forecast(power_values[-12:] if len(power_values) >= 12 else power_values, forecast_horizon)
    
    # Energy forecast (cumulative)
    energy_forecast = []
    cumulative_energy = energy_values[-1] if energy_values else 0
    for p in power_forecast:
        cumulative_energy += p / 3600  # Power (W) to Wh, assuming 1 second interval
        energy_forecast.append(cumulative_energy)
    
    # Cost forecast
    cost_forecast = [e * electricity_rate for e in energy_forecast]
    
    # Calculate projections
    hourly_cost = avg_power / 1000 * electricity_rate  # kW * rate
    daily_cost = hourly_cost * 24
    monthly_cost = daily_cost * 30
    
    return {
        "data": [dict(r) for r in rows],
        "forecast": {
            "power": power_forecast,
            "energy": energy_forecast,
            "cost": cost_forecast
        },
        "summary": {
            "avg_power": round(avg_power, 2),
            "avg_current": round(avg_current, 2),
            "projected_hourly_cost": round(hourly_cost, 4),
            "projected_daily_cost": round(daily_cost, 2),
            "projected_monthly_cost": round(monthly_cost, 2),
            "electricity_rate": electricity_rate,
            "trend": "increasing" if power_forecast[-1] > power_forecast[0] else "decreasing" if power_forecast[-1] < power_forecast[0] else "stable"
        }
    }