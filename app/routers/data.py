from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from app.schemas import SensorPayload
from app.services.prediction import run_predictions
from app.services.ml_prediction import run_ml_predictions, ml_prediction_service
from app.services.advanced_ml_prediction import run_advanced_ml_predictions, advanced_ml_prediction_service
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

    # Run Advanced ML predictions with configurable options
    prediction_mode = getattr(settings, 'prediction_mode', 'advanced')  # 'basic', 'ml', 'advanced'
    
    if prediction_mode == 'advanced':
        predictions = await run_advanced_ml_predictions(payload, db)
    elif prediction_mode == 'ml':
        predictions = await run_ml_predictions(payload, db)
    else:
        predictions = run_predictions(payload)  # Basic rule-based
    
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

@router.post("/ai/analyze/{device_id}")
async def analyze_with_gemini(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """On-demand Gemini AI analysis - separate from automatic ML predictions"""
    # Get latest sensor data for this device
    result = await db.execute(text("""
        SELECT * FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT 1
    """), {"device_id": device_id})
    row = result.mappings().first()
    
    if not row:
        raise HTTPException(status_code=404, detail="No sensor data found for device")
    
    # Reconstruct payload from database row using the actual schema model names
    from app.schemas import (
        FaultsData,
        MaintenanceData,
        MotorData,
        PowerData,
        ProtectionData,
        SensorPayload,
        TemperatureData,
        VibrationData,
    )
    
    payload = SensorPayload(
        deviceId=device_id,
        motor=MotorData(
            running=row['motor_running'],
            rpm=row['rpm'],
            pulse=row['pulse'],
            uptime=row['uptime_seconds']
        ),
        power=PowerData(
            voltage=row['voltage'],
            current=row['current'],
            power=row['power'],
            powerFactor=row['power_factor'],
            energy=row['energy'],
            frequency=row['frequency']
        ),
        temperature=TemperatureData(
            t1=row['temp1'],
            t2=row['temp2']
        ),
        vibration=VibrationData(
            x=row['accel_x'],
            y=row['accel_y'],
            z=row['accel_z'],
            tap=row['tap_detected']
        ),
        faults=FaultsData(
            overcurrent=row['fault_overcurrent'],
            overtemp=row['fault_overtemp'],
            stall=row['fault_stall'],
            vibration=row['fault_vibration'],
            overvoltage=row['fault_overvoltage'],
            undervoltage=row['fault_undervoltage']
        ),
        protection=ProtectionData(
            maxCurrentA=row['prot_max_current'],
            maxTempC=row['prot_max_temp'],
            minRpm=row['prot_min_rpm'],
            overvoltageV=row['prot_overvoltage'],
            undervoltageV=row['prot_undervoltage'],
            stallCurrentA=row['prot_stall_current'],
            startupGraceMs=row['prot_startup_grace'],
            faultTripCount=row['prot_fault_trip_count'],
            vibrationAckGraceMs=row['prot_vibration_ack_grace']
        ),
        maintenance=MaintenanceData(
            nextMaintenanceTime=row['maint_next_time'],
            totalLifeCycleHours=row['maint_total_hours'],
            maintenanceHoursLimit=row['maint_hours_limit'],
            totalLifeCycleSeconds=row['maint_total_seconds'],
            maintenanceHoursLimitSeconds=row['maint_limit_seconds']
        ),
        uptime=row['uptime_seconds']
    )
    
    # Call appropriate Gemini service based on prediction mode
    prediction_mode = getattr(settings, 'prediction_mode', 'advanced')
    
    if prediction_mode == 'advanced':
        gemini_result = await advanced_ml_prediction_service.get_gemini_analysis(payload, db)
    else:
        gemini_result = await ml_prediction_service.get_gemini_commentary(payload, db)
    
    if gemini_result:
        # Store the AI analysis as a prediction
        await db.execute(text("""
            INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
            VALUES (:device_id, :type, :confidence, :severity, :details)
        """), {
            "device_id": device_id,
            "type": gemini_result["type"],
            "confidence": gemini_result["confidence"],
            "severity": gemini_result["severity"],
            "details": json.dumps(gemini_result["details"])
        })
        await db.commit()
        
        return {
            "success": True,
            "analysis": gemini_result,
            "message": "Gemini AI analysis completed and stored"
        }
    else:
        gemini_error = getattr(advanced_ml_prediction_service, 'last_gemini_error', '') or ''
        if 'RESOURCE_EXHAUSTED' in gemini_error or 'quota' in gemini_error.lower():
            message = "Gemini request hit the current Google quota limit for this project. Try again later or use a project with available quota."
        elif gemini_error:
            message = f"Gemini AI analysis failed: {gemini_error}"
        else:
            message = "Gemini AI analysis failed or is not configured. Set GEMINI_API_KEY in the backend .env file."
        return {
            "success": False,
            "analysis": None,
            "message": message
        }
