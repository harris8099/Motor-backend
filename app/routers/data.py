from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from fastapi.responses import StreamingResponse
import io
import csv

# India timezone (IST = UTC+5:30)
INDIA_TZ = timezone(timedelta(hours=5, minutes=30))
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from app.schemas import (
    SensorPayload, FaultsData, MaintenanceData, MotorData,
    PowerData, ProtectionData, TemperatureData, VibrationData,
    AckFaultsCommand, SetProtectionCommand, SetMaintenanceCommand,
    SetRuntimeCommand, EmptyCommand,
)
from app.services.prediction import run_predictions
from app.services.ml_prediction import run_ml_predictions, ml_prediction_service
from app.services.advanced_ml_prediction import run_advanced_ml_predictions, advanced_ml_prediction_service
from app.routers.faults import detect_and_log_fault
import json
import httpx
import numpy as np
from pydantic import BaseModel, ValidationError


# ── Custom JSON encoder to handle numpy types from sklearn/numpy ──────────────
class NumpyEncoder(json.JSONEncoder):
    """Converts numpy scalar types (numpy.bool_, numpy.float64, etc.) to
    native Python types so json.dumps() never raises TypeError.
    Also handles NaN/inf values which PostgreSQL JSON doesn't accept."""
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            val = float(obj)
            # PostgreSQL JSON doesn't accept NaN or Infinity
            if np.isnan(val) or np.isinf(val):
                return None
            return val
        if isinstance(obj, np.ndarray):
            # Convert array and handle NaN/inf within it
            return [None if (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) else x 
                    for x in obj.tolist()]
        return super().default(obj)


def convert_numpy_value(val):
    """Convert numpy scalar to Python native type, handling NaN/inf."""
    if isinstance(val, (np.floating, np.float64, np.float32)):
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, np.bool_):
        return bool(val)
    return val


def _convert_dict_numpy_values(obj):
    """Recursively convert numpy values in dict/list to native Python types."""
    if isinstance(obj, dict):
        return {k: _convert_dict_numpy_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_dict_numpy_values(v) for v in obj]
    return convert_numpy_value(obj)


def sanitize_for_json(obj):
    """
    Recursively sanitize an object for JSON serialization.
    Handles both numpy types and native Python floats with NaN/inf.
    PostgreSQL JSON columns do not accept NaN or Infinity values.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        f = float(obj)
        return None if (np.isnan(f) or np.isinf(f)) else f
    if isinstance(obj, float):
        # Native Python float - check for NaN/inf
        return None if (np.isnan(obj) or np.isinf(obj)) else obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    return obj

async def _fetch_city_temp(lat: float, lon: float) -> float | None:
    """Fetch current city temperature from Open-Meteo (no API key needed)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon, "current": "temperature_2m"}
            )
            return r.json()["current"]["temperature_2m"]
    except Exception:
        return None

router = APIRouter()

_GEMINI_COOLDOWN_SECONDS = 30
_COMMAND_EXPIRY_INTERVAL = "5 minutes"
_COMMAND_REPLACEMENT_GROUPS = {
    "set_protection": ("set_protection",),
    "set_maintenance": ("set_maintenance", "set_runtime", "clear_maintenance"),
    "set_runtime": ("set_maintenance", "set_runtime", "clear_maintenance"),
    "clear_maintenance": ("set_maintenance", "set_runtime", "clear_maintenance"),
    "reset_energy": ("reset_energy", "reset_power"),
    "reset_power": ("reset_energy", "reset_power"),
}


async def _queue_device_command(
    db: AsyncSession,
    device_id: str,
    command: str,
    payload_json: str,
) -> dict:
    replaced_commands = list(_COMMAND_REPLACEMENT_GROUPS.get(command, ()))
    replaced_count = 0

    if replaced_commands:
        command_list_sql = ", ".join(f"'{name}'" for name in replaced_commands)
        replaced_result = await db.execute(text(f"""
            UPDATE commands
            SET status='cancelled', acked_at=NOW()
            WHERE device_id=:did
              AND status='pending'
              AND command IN ({command_list_sql})
        """), {"did": device_id})
        replaced_count = replaced_result.rowcount or 0

    await db.execute(text("""
        INSERT INTO commands (device_id, command, payload)
        VALUES (:did, :command, :payload)
    """), {"did": device_id, "command": command, "payload": payload_json})
    await db.commit()

    return {
        "ok": True,
        "replacedPendingCommands": replaced_count,
        "replacementGroup": replaced_commands,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Shared helper: DB row → SensorPayload ────────────────────────────────────
def _row_to_payload(device_id: str, row) -> SensorPayload:
    """Convert a sensor_readings DB row back into a SensorPayload object."""
    return SensorPayload(
        deviceId=device_id,
        motor=MotorData(
            running=row['motor_running'],
            rpm=row['rpm'],
            pulse=row['pulse'],
            uptime=row['uptime_seconds'],
        ),
        power=PowerData(
            voltage=row['voltage'],
            current=row['current'],
            power=row['power'],
            powerFactor=row['power_factor'],
            energy=row['energy'],
            frequency=row['frequency'],
        ),
        temperature=TemperatureData(t1=row['temp1'], t2=row['temp2']),
        vibration=VibrationData(
            x=row['accel_x'], y=row['accel_y'], z=row['accel_z'],
            tap=row['tap_detected'],
        ),
        faults=FaultsData(
            overcurrent=row['fault_overcurrent'],
            overtemp=row['fault_overtemp'],
            stall=row['fault_stall'],
            vibration=row['fault_vibration'],
            overvoltage=row['fault_overvoltage'],
            undervoltage=row['fault_undervoltage'],
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
            vibrationAckGraceMs=row['prot_vibration_ack_grace'],
        ),
        maintenance=MaintenanceData(
            nextMaintenanceTime=row['maint_next_time'],
            totalLifeCycleHours=row['maint_total_hours'],
            maintenanceHoursLimit=row['maint_hours_limit'],
            totalLifeCycleSeconds=row['maint_total_seconds'],
            maintenanceHoursLimitSeconds=row['maint_limit_seconds'],
        ),
        uptime=row['uptime_seconds'],
    )


# ── POST /data ────────────────────────────────────────────────────────────────
@router.post("/data")
async def receive_data(
    payload: SensorPayload,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    previous_faults = await db.execute(text("""
        SELECT fault_overcurrent, fault_overtemp, fault_stall,
               fault_vibration, fault_overvoltage, fault_undervoltage
        FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC
        LIMIT 1
    """), {"device_id": payload.deviceId})
    previous_fault_row = previous_faults.mappings().first()

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
        "temp2": await _fetch_city_temp(24.58, 73.68) if payload.temperature.t2 == 0 else payload.temperature.t2,
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

    await db.commit()

    # Get the ID of the inserted reading for fault logging reference
    reading_result = await db.execute(text("""
        SELECT id FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC
        LIMIT 1
    """), {"device_id": payload.deviceId})
    reading_row = reading_result.mappings().first()
    reading_id = reading_row["id"] if reading_row else None

    # Log new fault activations using the enhanced fault system
    current_faults = payload.faults.model_dump()
    previous_faults = {
        key.replace("fault_", ""): bool(previous_fault_row[key]) if previous_fault_row else False
        for key in (
            "fault_overcurrent",
            "fault_overtemp",
            "fault_stall",
            "fault_vibration",
            "fault_overvoltage",
            "fault_undervoltage",
        )
    }
    activated_faults = [
        fault_name
        for fault_name, is_active in current_faults.items()
        if is_active and not previous_faults.get(fault_name, False)
    ]

    # Use the new detect_and_log_fault function for each activated fault
    for fault_type in activated_faults:
        await detect_and_log_fault(db, payload.deviceId, fault_type, reading_id)

    # Run ML predictions
    prediction_mode = getattr(settings, 'prediction_mode', 'advanced')
    if prediction_mode == 'advanced':
        predictions = await run_advanced_ml_predictions(payload, db)
    elif prediction_mode == 'ml':
        predictions = await run_ml_predictions(payload, db)
    else:
        predictions = run_predictions(payload)

    for p in predictions:
        # Convert numpy values including NaN to None for PostgreSQL compatibility
        confidence = convert_numpy_value(p["confidence"])
        details_dict = _convert_dict_numpy_values(p["details"]) if p["details"] else {}
        
        await db.execute(text("""
            INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
            VALUES (:device_id, :type, :confidence, :severity, :details)
        """), {
            "device_id": payload.deviceId,
            "type": p["type"],
            "confidence": confidence,
            "severity": p["severity"],
            "details": json.dumps(details_dict, cls=NumpyEncoder),
        })

    # ── Auto-cleanup: prevent unbounded table growth ──────────────────────────
    await db.execute(text("""
        DELETE FROM predictions
        WHERE device_id = :device_id
          AND ts < NOW() - INTERVAL '7 days'
    """), {"device_id": payload.deviceId})

    await db.execute(text("""
        DELETE FROM sensor_readings
        WHERE device_id = :device_id
          AND ts < NOW() - INTERVAL '30 days'
    """), {"device_id": payload.deviceId})
    # ─────────────────────────────────────────────────────────────────────────

    await db.commit()
    return {"ok": True}


# ── GET /data/{device_id} ────────────────────────────────────────────────────
@router.get("/data/{device_id}")
async def get_readings(
    device_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    result = await db.execute(text("""
        SELECT id, device_id, ts,
               motor_running, rpm, pulse, uptime_seconds,
               voltage, current, power, power_factor, energy, frequency,
               temp1, temp2,
               accel_x, accel_y, accel_z, tap_detected,
               fault_overcurrent, fault_overtemp, fault_stall,
               fault_vibration, fault_overvoltage, fault_undervoltage,
               prot_max_current, prot_max_temp, prot_min_rpm,
               prot_overvoltage AS prot_overvoltage_v,
               prot_undervoltage AS prot_undervoltage_v,
               prot_stall_current AS prot_stall_current_a,
               prot_startup_grace AS prot_startup_grace_ms,
               prot_fault_trip_count,
               prot_vibration_ack_grace AS prot_vibration_ack_grace_ms,
               maint_next_time,
               maint_total_hours,
               maint_hours_limit,
               maint_total_seconds,
               maint_limit_seconds
        FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT :limit
    """), {"device_id": device_id, "limit": limit})
    rows = result.mappings().all()
    return {"data": [dict(r) for r in rows]}


# ── POST /ai/analyze/{device_id} ─────────────────────────────────────────────
@router.post("/ai/analyze/{device_id}")
async def analyze_with_ai(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """On-demand Cloud AI analysis (Mistral → Gemini → Groq) with DB-backed cooldown."""

    # ── DB-backed cooldown (survives server restarts) ─────────────────────────
    cooldown_res = await db.execute(text("""
        SELECT last_ai_analysis_at FROM devices WHERE id = :device_id
    """), {"device_id": device_id})
    device_row = cooldown_res.mappings().first()

    if device_row and device_row['last_ai_analysis_at']:
        last_call = device_row['last_ai_analysis_at']
        now = datetime.now(timezone.utc)
        if last_call.tzinfo is None:
            last_call = last_call.replace(tzinfo=timezone.utc)
        elapsed = (now - last_call).total_seconds()
        if elapsed < _GEMINI_COOLDOWN_SECONDS:
            wait = int(_GEMINI_COOLDOWN_SECONDS - elapsed)
            return {
                "success": False,
                "analysis": None,
                "message": f"Please wait {wait} more second(s) before requesting another AI analysis for this device.",
            }

    # Mark cooldown start (upsert so it works even if device row is missing)
    await db.execute(text("""
        INSERT INTO devices (id, name, last_seen_at, updated_at, is_active, last_ai_analysis_at)
        VALUES (:device_id, :device_id, NOW(), NOW(), TRUE, NOW())
        ON CONFLICT (id) DO UPDATE SET last_ai_analysis_at = NOW()
    """), {"device_id": device_id})
    await db.commit()
    # ─────────────────────────────────────────────────────────────────────────

    # Get latest sensor reading
    result = await db.execute(text("""
        SELECT * FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT 1
    """), {"device_id": device_id})
    row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="No sensor data found for device")

    payload = _row_to_payload(device_id, row)

    # Call AI service (Mistral → Gemini → Groq fallback)
    ai_result = await advanced_ml_prediction_service.get_ai_analysis(payload, db)

    if ai_result:
        # Sanitize all values for PostgreSQL JSON compatibility (no NaN/inf allowed)
        confidence = sanitize_for_json(ai_result["confidence"])
        details_dict = sanitize_for_json(ai_result["details"]) if ai_result["details"] else {}

        await db.execute(text("""
            INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
            VALUES (:device_id, :type, :confidence, :severity, :details)
        """), {
            "device_id": device_id,
            "type": ai_result["type"],
            "confidence": confidence,
            "severity": ai_result["severity"],
            "details": json.dumps(details_dict, cls=NumpyEncoder),
        })
        await db.commit()
        return {"success": True, "analysis": ai_result, "message": "AI analysis completed and stored"}
    else:
        ai_error = getattr(advanced_ml_prediction_service, 'last_ai_error', '') or 'AI analysis failed or is not configured.'
        return {"success": False, "analysis": None, "message": ai_error}


# ── GET /ai/latest/{device_id} ───────────────────────────────────────────────
@router.get("/ai/latest/{device_id}")
async def get_latest_ai_result(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Return the latest commentary AND latest prediction for a device separately."""

    def _parse_row(row):
        if not row:
            return None
        r = dict(row)
        if isinstance(r.get('details'), str):
            try:
                r['details'] = json.loads(r['details'])
            except Exception:
                pass
        return r

    commentary_res = await db.execute(text("""
        SELECT id, device_id, prediction_type, confidence, severity, details,
               ts AS predicted_at
        FROM predictions
        WHERE device_id = :device_id AND prediction_type = 'ai_comment'
        ORDER BY ts DESC LIMIT 1
    """), {"device_id": device_id})

    prediction_res = await db.execute(text("""
        SELECT id, device_id, prediction_type, confidence, severity, details,
               ts AS predicted_at
        FROM predictions
        WHERE device_id = :device_id AND prediction_type = 'ai_analysis'
        ORDER BY ts DESC LIMIT 1
    """), {"device_id": device_id})

    return {
        "commentary": _parse_row(commentary_res.mappings().first()),
        "prediction": _parse_row(prediction_res.mappings().first()),
    }


# ── POST /ai/mode ─────────────────────────────────────────────────────────────
class AIModeRequest(BaseModel):
    mode: str  # 'commentary' | 'prediction' | 'disabled'


@router.post("/ai/mode")
async def set_ai_mode(
    body: AIModeRequest,
    _: None = Depends(verify_api_key),
):
    """Change the AI analysis mode at runtime without restarting the server."""
    if body.mode not in ('commentary', 'prediction', 'disabled'):
        raise HTTPException(status_code=400, detail="mode must be 'commentary', 'prediction', or 'disabled'")
    advanced_ml_prediction_service.gemini_mode = body.mode
    if hasattr(ml_prediction_service, 'gemini_mode'):
        ml_prediction_service.gemini_mode = body.mode
    return {"success": True, "mode": body.mode, "message": f"AI mode updated to '{body.mode}'"}


# ── POST /ai/local-analyze/{device_id} ───────────────────────────────────────
@router.post("/ai/local-analyze/{device_id}")
async def analyze_with_local_models(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """On-demand trigger for local ML models (Isolation Forest, RUL, etc.)"""
    result = await db.execute(text("""
        SELECT * FROM sensor_readings
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT 1
    """), {"device_id": device_id})
    row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="No sensor data found for device")

    payload = _row_to_payload(device_id, row)

    from app.services import advanced_ml_prediction as adv_module
    from app.services import ml_prediction as ml_module
    from app.services.prediction import run_predictions as run_basic

    prediction_mode = getattr(settings, 'prediction_mode', 'advanced')
    if prediction_mode == 'advanced':
        predictions = await adv_module.run_advanced_ml_predictions(payload, db)
    elif prediction_mode == 'ml':
        predictions = await ml_module.run_ml_predictions(payload, db)
    else:
        predictions = run_basic(payload)

    for p in predictions:
        # Sanitize all values for PostgreSQL JSON compatibility (no NaN/inf allowed)
        confidence = sanitize_for_json(p["confidence"])
        details_dict = sanitize_for_json(p["details"]) if p["details"] else {}

        await db.execute(text("""
            INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
            VALUES (:device_id, :type, :confidence, :severity, :details)
        """), {
            "device_id": payload.deviceId,
            "type": p["type"],
            "confidence": confidence,
            "severity": p["severity"],
            "details": json.dumps(details_dict, cls=NumpyEncoder),
        })
    await db.commit()
    return {"success": True, "generated": len(predictions), "message": f"Successfully ran {len(predictions)} local models."}


# ── POST /command/{device_id}/ack_faults ──────────────────────────────────────
@router.post("/command/{device_id}/ack_faults")
async def cmd_ack_faults(
    device_id: str,
    body: AckFaultsCommand = Body(default_factory=AckFaultsCommand),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue an ack_faults command for the device. body may contain {faults: ['overcurrent', ...]}."""
    return await _queue_device_command(
        db,
        device_id,
        "ack_faults",
        body.model_dump_json(exclude_none=True),
    )


# ── POST /command/{device_id}/set_protection ──────────────────────────────────
@router.post("/command/{device_id}/set_protection")
async def cmd_set_protection(
    device_id: str,
    body: SetProtectionCommand,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue a set_protection command with updated threshold values."""
    return await _queue_device_command(
        db,
        device_id,
        "set_protection",
        body.model_dump_json(exclude_none=True),
    )


@router.post("/command/{device_id}/set_maintenance")
async def cmd_set_maintenance(
    device_id: str,
    body: SetMaintenanceCommand,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue a set_maintenance command with maintenance and optional runtime values."""
    return await _queue_device_command(
        db,
        device_id,
        "set_maintenance",
        body.model_dump_json(exclude_none=True),
    )


@router.post("/command/{device_id}/set_runtime")
async def cmd_set_runtime(
    device_id: str,
    body: SetRuntimeCommand,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue a set_runtime command with uptimeSeconds."""
    return await _queue_device_command(
        db,
        device_id,
        "set_runtime",
        body.model_dump_json(exclude_none=True),
    )


@router.post("/command/{device_id}/reset_energy")
async def cmd_reset_energy(
    device_id: str,
    body: EmptyCommand = Body(default_factory=EmptyCommand),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue a reset_energy command for the device."""
    return await _queue_device_command(
        db,
        device_id,
        "reset_energy",
        body.model_dump_json(exclude_none=True),
    )


@router.post("/command/{device_id}/reset_power")
async def cmd_reset_power(
    device_id: str,
    body: EmptyCommand = Body(default_factory=EmptyCommand),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Compatibility alias for reset_energy."""
    return await _queue_device_command(
        db,
        device_id,
        "reset_power",
        body.model_dump_json(exclude_none=True),
    )


@router.post("/command/{device_id}/clear_maintenance")
async def cmd_clear_maintenance(
    device_id: str,
    body: EmptyCommand = Body(default_factory=EmptyCommand),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Queue a clear_maintenance command for the device."""
    return await _queue_device_command(
        db,
        device_id,
        "clear_maintenance",
        body.model_dump_json(exclude_none=True),
    )


# ── GET /command/{device_id}/pending ─────────────────────────────────────────
@router.get("/command/{device_id}/pending")
async def cmd_get_pending(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Return the oldest pending command for this device (used by ESP32 poll)."""
    # Auto-expire commands older than 5 minutes
    await db.execute(text(f"""
        UPDATE commands SET status='expired'
        WHERE device_id=:did AND status='pending'
        AND created_at < NOW() - INTERVAL '{_COMMAND_EXPIRY_INTERVAL}'
    """), {"did": device_id})
    await db.commit()

    validator_map = {
        "ack_faults": AckFaultsCommand,
        "set_protection": SetProtectionCommand,
        "set_maintenance": SetMaintenanceCommand,
        "set_runtime": SetRuntimeCommand,
        "reset_energy": EmptyCommand,
        "reset_power": EmptyCommand,
        "clear_maintenance": EmptyCommand,
    }

    while True:
        result = await db.execute(text("""
            SELECT id, command, payload FROM commands
            WHERE device_id=:did AND status='pending'
            ORDER BY created_at ASC LIMIT 1
        """), {"did": device_id})
        row = result.mappings().first()

        if not row:
            return {"command": None}

        command = row["command"]
        payload = row["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = None

        validator = validator_map.get(command)
        if validator is None or (payload is not None and not isinstance(payload, dict)):
            await db.execute(text("""
                UPDATE commands SET status='failed', acked_at=NOW()
                WHERE id=:id AND device_id=:did AND status='pending'
            """), {"id": row["id"], "did": device_id})
            await db.commit()
            continue

        try:
            validated = validator.model_validate(payload or {})
        except ValidationError:
            await db.execute(text("""
                UPDATE commands SET status='failed', acked_at=NOW()
                WHERE id=:id AND device_id=:did AND status='pending'
            """), {"id": row["id"], "did": device_id})
            await db.commit()
            continue

        return {
            "id": row["id"],
            "command": command,
            "payload": validated.model_dump(exclude_none=True),
        }


@router.get("/command/{device_id}/history")
async def cmd_get_history(
    device_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Return recent commands for this device for debug/status UI."""
    safe_limit = max(1, min(limit, 50))
    result = await db.execute(text("""
        SELECT id, command, payload, status, created_at, acked_at
        FROM commands
        WHERE device_id=:did
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"did": device_id, "limit": safe_limit})

    rows = []
    for row in result.mappings().all():
        payload = row["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass

        rows.append({
            "id": row["id"],
            "command": row["command"],
            "payload": payload,
            "status": row["status"],
            "created_at": row["created_at"],
            "acked_at": row["acked_at"],
        })

    return {"commands": rows}


# ── POST /command/{device_id}/done ────────────────────────────────────────────
@router.post("/command/{device_id}/done")
async def cmd_done(
    device_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Mark a command as acknowledged by the device."""
    await db.execute(text("""
        UPDATE commands SET status='acked', acked_at=NOW()
        WHERE id=:id AND device_id=:did AND status='pending'
    """), {"id": body["id"], "did": device_id})
    await db.commit()
    return {"ok": True}


# ── GET /data/{device_id}/export ─────────────────────────────────────────────
@router.get("/data/{device_id}/export")
async def export_readings_csv(
    device_id: str,
    categories: str = None,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Export sensor readings as a CSV file."""
    
    CATEGORY_MAP = {
        "motor": ["motor_running", "rpm", "pulse", "uptime_seconds"],
        "power": ["voltage", "current", "power", "power_factor", "energy", "frequency"],
        "temperature": ["temp1", "temp2"],
        "vibration": ["accel_x", "accel_y", "accel_z", "tap_detected"],
        "faults": ["fault_overcurrent", "fault_overtemp", "fault_stall", "fault_vibration", "fault_overvoltage", "fault_undervoltage"]
    }
    
    selected_columns = ["ts"]
    
    if categories:
        cats = [c.strip().lower() for c in categories.split(",")]
        for cat in cats:
            if cat in CATEGORY_MAP:
                selected_columns.extend(CATEGORY_MAP[cat])
    
    if len(selected_columns) == 1:
        for cols in CATEGORY_MAP.values():
            selected_columns.extend(cols)
            
    columns_sql = ", ".join(selected_columns)

    count_query = "SELECT COUNT(*) FROM sensor_readings WHERE device_id = :device_id"
    query = f"SELECT {columns_sql} FROM sensor_readings WHERE device_id = :device_id"
    params = {"device_id": device_id}
    
    if start_date:
        query += " AND ts >= :start_date"
        count_query += " AND ts >= :start_date"
        params["start_date"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        query += " AND ts <= :end_date"
        count_query += " AND ts <= :end_date"
        params["end_date"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
    query += " ORDER BY ts ASC"

    count_result = await db.execute(text(count_query), params)
    if count_result.scalar() == 0:
        raise HTTPException(status_code=404, detail="No data found for the selected date range")

    async def iter_csv():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        result = await db.execute(text(query), params)
        rows = result.mappings().all()
            
        writer.writerow(rows[0].keys())
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        
        for row in rows:
            writer.writerow(row.values())
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            
    headers = {
        "Content-Disposition": f"attachment; filename=sensor_data_{device_id}.csv"
    }
    return StreamingResponse(iter_csv(), media_type="text/csv", headers=headers)
