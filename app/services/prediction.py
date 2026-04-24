from app.schemas import SensorPayload
from typing import List

def run_predictions(payload: SensorPayload) -> List[dict]:
    results = []

    # 1. Overheating trend
    avg_temp = (payload.temperature.t1 + payload.temperature.t2) / 2
    if avg_temp > payload.protection.maxTempC:
        results.append({
            "type": "overheating",
            "confidence": min((avg_temp - payload.protection.maxTempC) / 30, 1.0),
            "severity": "high" if avg_temp > (payload.protection.maxTempC + 10) else "medium",
            "details": {"avg_temp": avg_temp}
        })

    # 2. Stall risk — high current + dropping RPM
    if payload.power.current > payload.protection.stallCurrentA and payload.motor.rpm < payload.protection.minRpm:
        results.append({
            "type": "stall_risk",
            "confidence": 0.75,
            "severity": "high",
            "details": {"current": payload.power.current, "rpm": payload.motor.rpm}
        })

    # 3. Vibration anomaly
    magnitude = (payload.vibration.x**2 + payload.vibration.y**2 + payload.vibration.z**2) ** 0.5
    if magnitude > 2.5:
        results.append({
            "type": "bearing_fault",
            "confidence": min((magnitude - 2.5) / 2.0, 1.0),
            "severity": "medium",
            "details": {"vibration_magnitude": magnitude}
        })

    # 4. Maintenance Due
    if payload.maintenance.totalLifeCycleHours > payload.maintenance.maintenanceHoursLimit:
        results.append({
            "type": "maintenance_due",
            "confidence": 1.0,
            "severity": "high",
            "details": {"total_hours": payload.maintenance.totalLifeCycleHours, "limit": payload.maintenance.maintenanceHoursLimit}
        })

    return results
