from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from app.schemas import SensorPayload
from app.services.prediction import run_predictions
import json

router = APIRouter()

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post("/data")
async def receive_data(
    payload: SensorPayload,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    # Insert sensor reading
    await db.execute(text("""
        INSERT INTO sensor_readings (
            device_id, motor_running, rpm, pulse, uptime_seconds,
            voltage, current, power, power_factor, energy, frequency,
            temp1, temp2, accel_x, accel_y, accel_z, tap_detected,
            fault_overcurrent, fault_overtemp, fault_stall,
            fault_vibration, fault_overvoltage, fault_undervoltage,
            
            prot_max_current, prot_max_temp, prot_min_rpm,
            prot_overvoltage, prot_undervoltage, prot_stall_current,
            prot_startup_grace, prot_fault_trip_count, prot_vibration_ack_grace,
            
            maint_next_time, maint_total_hours, maint_hours_limit,
            maint_total_seconds, maint_limit_seconds
        ) VALUES (
            :device_id, :motor_running, :rpm, :pulse, :uptime,
            :voltage, :current, :power, :power_factor, :energy, :frequency,
            :temp1, :temp2, :accel_x, :accel_y, :accel_z, :tap,
            :f_oc, :f_ot, :f_stall, :f_vib, :f_ov, :f_uv,
            
            :p_max_c, :p_max_t, :p_min_rpm, :p_ov, :p_uv, :p_stall_c,
            :p_sg, :p_ftc, :p_vag,
            
            :m_next, :m_th, :m_hl, :m_ts, :m_ls
        )
    """), {
        "device_id": payload.deviceId,
        "motor_running": payload.motor.running,
        "rpm": payload.motor.rpm,
        "pulse": payload.motor.pulse,
        "uptime": payload.uptime,
        "voltage": payload.power.voltage,
        "current": payload.power.current,
        "power": payload.power.power,
        "power_factor": payload.power.powerFactor,
        "energy": payload.power.energy,
        "frequency": payload.power.frequency,
        "temp1": payload.temperature.t1,
        "temp2": payload.temperature.t2,
        "accel_x": payload.vibration.x,
        "accel_y": payload.vibration.y,
        "accel_z": payload.vibration.z,
        "tap": payload.vibration.tap,
        "f_oc": payload.faults.overcurrent,
        "f_ot": payload.faults.overtemp,
        "f_stall": payload.faults.stall,
        "f_vib": payload.faults.vibration,
        "f_ov": payload.faults.overvoltage,
        "f_uv": payload.faults.undervoltage,
        
        "p_max_c": payload.protection.maxCurrentA,
        "p_max_t": payload.protection.maxTempC,
        "p_min_rpm": payload.protection.minRpm,
        "p_ov": payload.protection.overvoltageV,
        "p_uv": payload.protection.undervoltageV,
        "p_stall_c": payload.protection.stallCurrentA,
        "p_sg": payload.protection.startupGraceMs,
        "p_ftc": payload.protection.faultTripCount,
        "p_vag": payload.protection.vibrationAckGraceMs,
        
        "m_next": payload.maintenance.nextMaintenanceTime,
        "m_th": payload.maintenance.totalLifeCycleHours,
        "m_hl": payload.maintenance.maintenanceHoursLimit,
        "m_ts": payload.maintenance.totalLifeCycleSeconds,
        "m_ls": payload.maintenance.maintenanceHoursLimitSeconds,
    })

    # Update device heartbeat (last_seen_at)
    await db.execute(text("""
        INSERT INTO devices (id, name, last_seen_at, updated_at, is_active)
        VALUES (:device_id, :device_id, NOW(), NOW(), TRUE)
        ON CONFLICT (id) DO UPDATE SET
            last_seen_at = NOW(),
            updated_at = NOW(),
            is_active = TRUE
    """), {"device_id": payload.deviceId})

    # Log active faults
    active = [k for k, v in payload.faults.model_dump().items() if v]
    for fault in active:
        await db.execute(text("""
            INSERT INTO fault_events (device_id, fault_type)
            VALUES (:device_id, :fault_type)
        """), {"device_id": payload.deviceId, "fault_type": fault})

    # Run predictions
    predictions = run_predictions(payload)
    for p in predictions:
        await db.execute(text("""
            INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
            VALUES (:device_id, :type, :confidence, :severity, :details)
        """), {
            "device_id": payload.deviceId,
            "type": p["type"],
            "confidence": p["confidence"],
            "severity": p["severity"],
            "details": json.dumps(p["details"])
        })

    await db.commit()
    return {"ok": True}


@router.get("/data/{device_id}")
async def get_readings(
    device_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    result = await db.execute(text("""
        SELECT * FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT :limit
    """), {"device_id": device_id, "limit": limit})
    rows = result.mappings().all()
    return {"data": [dict(r) for r in rows]}
