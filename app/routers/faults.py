from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
import io
import csv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from app.routers.auth import require_admin_user, User
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Enums and Models
# ─────────────────────────────────────────────────────────────────────────────

class FaultSeverity(str, Enum):
    CRITICAL = "critical"    # Motor stopped, overtemp, severe mechanical failure
    WARNING = "warning"      # High vibration, power fluctuation
    INFO = "info"            # Maintenance due, calibration needed

class FaultStatus(str, Enum):
    ACTIVE = "active"
    CLEARED_PENDING_CLOSE = "cleared_pending_close"
    RESOLVED = "resolved"

class RootCause(str, Enum):
    POWER_ISSUE = "power_issue"
    MECHANICAL_FAILURE = "mechanical_failure"
    SENSOR_ERROR = "sensor_error"
    SOFTWARE_BUG = "software_bug"
    WEAR_AND_TEAR = "wear_and_tear"
    OVERLOAD = "overload"
    ENVIRONMENTAL = "environmental"
    OTHER = "other"

class FaultCreate(BaseModel):
    device_id: str
    fault_type: str
    severity: FaultSeverity
    message: Optional[str] = None

class FaultResolve(BaseModel):
    root_cause: RootCause
    actions_taken: str
    parts_replaced: Optional[str] = None
    resolved_by: str
    notes: Optional[str] = None

class FaultResponse(BaseModel):
    id: int
    device_id: str
    device_name: Optional[str] = None
    fault_type: str
    severity: str
    status: str
    message: Optional[str] = None
    detected_at: datetime
    cleared_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    root_cause: Optional[str] = None
    actions_taken: Optional[str] = None
    parts_replaced: Optional[str] = None
    resolution_notes: Optional[str] = None
    sensor_reading_id: Optional[int] = None

# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ─────────────────────────────────────────────────────────────────────────────
# Fault Type to Severity Mapping (for auto-detection)
# ─────────────────────────────────────────────────────────────────────────────

FAULT_SEVERITY_MAP = {
    # Critical faults
    "overcurrent": FaultSeverity.CRITICAL,
    "overtemp": FaultSeverity.CRITICAL,
    "stall": FaultSeverity.CRITICAL,
    "overvoltage": FaultSeverity.CRITICAL,
    "undervoltage": FaultSeverity.CRITICAL,
    # Warning faults
    "vibration": FaultSeverity.WARNING,
    "high_current": FaultSeverity.WARNING,
    "high_temp": FaultSeverity.WARNING,
    # Info
    "maintenance_due": FaultSeverity.INFO,
    "calibration_needed": FaultSeverity.INFO,
}

FAULT_MESSAGES = {
    "overcurrent": "Motor drawing excessive current - check for mechanical overload or short circuit",
    "overtemp": "Motor temperature exceeds safe limits - inspect cooling system and ventilation",
    "stall": "Motor stalled - check for mechanical blockage or insufficient power",
    "overvoltage": "Supply voltage too high - check power regulator and grid stability",
    "undervoltage": "Supply voltage too low - insufficient power may cause motor damage",
    "vibration": "Excessive vibration detected - inspect bearings, alignment, and mounting",
    "high_current": "Current above normal operating range - monitor for developing issues",
    "high_temp": "Temperature elevated - monitor cooling system performance",
    "maintenance_due": "Scheduled maintenance interval reached",
    "calibration_needed": "Sensor calibration required for accurate readings",
}

# ─────────────────────────────────────────────────────────────────────────────
# Database Table Creation (runs on startup via main.py)
# ─────────────────────────────────────────────────────────────────────────────

CREATE_FAULT_LOGS_TABLE = """
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
);

CREATE INDEX IF NOT EXISTS idx_fault_logs_device_active 
ON fault_logs(device_id, status) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_fault_logs_detected_at 
ON fault_logs(detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_fault_logs_severity 
ON fault_logs(severity) WHERE status = 'active';
"""

# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/faults/active", response_model=List[FaultResponse])
async def get_active_faults(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get all active faults across all devices with device names."""
    result = await db.execute(text("""
        SELECT 
            f.id, f.device_id, d.name as device_name, f.fault_type, f.severity,
            f.status, f.message, f.detected_at, f.cleared_at, f.resolved_at, f.resolved_by,
            f.root_cause, f.actions_taken, f.parts_replaced, f.resolution_notes,
            f.sensor_reading_id
        FROM fault_logs f
        LEFT JOIN devices d ON f.device_id = d.id
        WHERE f.status = 'active'
        ORDER BY 
            CASE f.severity 
                WHEN 'critical' THEN 1 
                WHEN 'warning' THEN 2 
                ELSE 3 
            END,
            f.detected_at DESC
    """))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/faults/summary")
async def get_faults_summary(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get summary of active faults by severity for banner display."""
    result = await db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE severity = 'critical' AND status = 'active') as critical_count,
            COUNT(*) FILTER (WHERE severity = 'warning' AND status = 'active') as warning_count,
            COUNT(*) FILTER (WHERE severity = 'info' AND status = 'active') as info_count,
            COUNT(*) FILTER (WHERE status = 'active') as total_active
        FROM fault_logs
    """))
    row = result.mappings().first()
    return dict(row)


@router.get("/faults/device/{device_id}", response_model=List[FaultResponse])
async def get_device_faults(
    device_id: str,
    status: Optional[str] = None,  # 'active', 'cleared_pending_close', 'resolved', or None for all
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get fault history for a specific device."""
    query = """
        SELECT 
            f.id, f.device_id, d.name as device_name, f.fault_type, f.severity,
            f.status, f.message, f.detected_at, f.cleared_at, f.resolved_at, f.resolved_by,
            f.root_cause, f.actions_taken, f.parts_replaced, f.resolution_notes,
            f.sensor_reading_id
        FROM fault_logs f
        LEFT JOIN devices d ON f.device_id = d.id
        WHERE f.device_id = :device_id
    """
    params = {"device_id": device_id, "limit": limit}
    
    if status:
        if status not in {member.value for member in FaultStatus}:
            raise HTTPException(status_code=400, detail=f"Unsupported status '{status}'")
        query += " AND f.status = :status"
        params["status"] = status
    
    query += " ORDER BY f.detected_at DESC LIMIT :limit"
    
    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/faults", response_model=List[FaultResponse])
async def get_all_faults(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get all faults with optional filtering."""
    query = """
        SELECT 
            f.id, f.device_id, d.name as device_name, f.fault_type, f.severity,
            f.status, f.message, f.detected_at, f.cleared_at, f.resolved_at, f.resolved_by,
            f.root_cause, f.actions_taken, f.parts_replaced, f.resolution_notes,
            f.sensor_reading_id
        FROM fault_logs f
        LEFT JOIN devices d ON f.device_id = d.id
        WHERE 1=1
    """
    params = {"limit": limit, "offset": offset}
    
    if status:
        if status not in {member.value for member in FaultStatus}:
            raise HTTPException(status_code=400, detail=f"Unsupported status '{status}'")
        query += " AND f.status = :status"
        params["status"] = status
    if severity:
        query += " AND f.severity = :severity"
        params["severity"] = severity
    if device_id:
        query += " AND f.device_id = :device_id"
        params["device_id"] = device_id
    
    query += " ORDER BY f.detected_at DESC LIMIT :limit OFFSET :offset"
    
    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.post("/faults", response_model=FaultResponse)
async def create_fault(
    fault: FaultCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Manually create a fault log entry (for admin use)."""
    message = fault.message or FAULT_MESSAGES.get(fault.fault_type, f"Fault detected: {fault.fault_type}")
    
    result = await db.execute(text("""
        INSERT INTO fault_logs (device_id, fault_type, severity, status, message)
        VALUES (:device_id, :fault_type, :severity, 'active', :message)
        RETURNING id
    """), {
        "device_id": fault.device_id,
        "fault_type": fault.fault_type,
        "severity": fault.severity.value,
        "message": message
    })
    fault_id = result.scalar()
    await db.commit()
    
    # Return the created fault
    return await _get_fault_by_id(db, fault_id)


@router.post("/faults/{fault_id}/resolve", response_model=FaultResponse)
async def resolve_fault(
    fault_id: int,
    resolution: FaultResolve,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Resolve a fault by filling out the resolution form."""
    # Check if fault exists and is active
    check = await db.execute(text("""
        SELECT status FROM fault_logs WHERE id = :fault_id
    """), {"fault_id": fault_id})
    row = check.mappings().first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Fault not found")
    if row["status"] == FaultStatus.RESOLVED.value:
        raise HTTPException(status_code=400, detail="Fault is already resolved")
    
    # Update the fault
    await db.execute(text("""
        UPDATE fault_logs SET
            status = 'resolved',
            resolved_at = NOW(),
            resolved_by = :resolved_by,
            root_cause = :root_cause,
            actions_taken = :actions_taken,
            parts_replaced = :parts_replaced,
            resolution_notes = :notes
        WHERE id = :fault_id
    """), {
        "fault_id": fault_id,
        "resolved_by": resolution.resolved_by,
        "root_cause": resolution.root_cause.value,
        "actions_taken": resolution.actions_taken,
        "parts_replaced": resolution.parts_replaced,
        "notes": resolution.notes
    })
    await db.commit()
    
    return await _get_fault_by_id(db, fault_id)


@router.delete("/faults/{fault_id}")
async def delete_fault(
    fault_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Delete a fault log entry (admin only)."""
    result = await db.execute(text("""
        DELETE FROM fault_logs WHERE id = :fault_id
        RETURNING id
    """), {"fault_id": fault_id})
    deleted = result.scalar()
    await db.commit()
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Fault not found")
    
    return {"message": "Fault deleted successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

async def _get_fault_by_id(db: AsyncSession, fault_id: int) -> dict:
    """Get a single fault by ID with device name."""
    result = await db.execute(text("""
        SELECT 
            f.id, f.device_id, d.name as device_name, f.fault_type, f.severity,
            f.status, f.message, f.detected_at, f.cleared_at, f.resolved_at, f.resolved_by,
            f.root_cause, f.actions_taken, f.parts_replaced, f.resolution_notes,
            f.sensor_reading_id
        FROM fault_logs f
        LEFT JOIN devices d ON f.device_id = d.id
        WHERE f.id = :fault_id
    """), {"fault_id": fault_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Fault not found")
    return dict(row)


async def detect_and_log_fault(
    db: AsyncSession,
    device_id: str,
    fault_type: str,
    sensor_reading_id: Optional[int] = None
) -> Optional[dict]:
    """
    Detect and log a fault when sensor data indicates a fault condition.
    Only creates a new fault log if there isn't already an active fault of the same type.
    Returns the created fault or None if skipped (duplicate active fault).
    """
    # Check if there's already an active fault of this type for this device
    check = await db.execute(text("""
        SELECT id FROM fault_logs
        WHERE device_id = :device_id 
        AND fault_type = :fault_type 
        AND status = 'active'
        LIMIT 1
    """), {"device_id": device_id, "fault_type": fault_type})
    
    if check.mappings().first():
        # Active fault already exists, don't create duplicate
        return None
    
    # Determine severity and message
    severity = FAULT_SEVERITY_MAP.get(fault_type, FaultSeverity.WARNING)
    message = FAULT_MESSAGES.get(fault_type, f"Fault detected: {fault_type}")
    
    # Create the fault log
    result = await db.execute(text("""
        INSERT INTO fault_logs (device_id, fault_type, severity, status, message, sensor_reading_id)
        VALUES (:device_id, :fault_type, :severity, 'active', :message, :sensor_reading_id)
        RETURNING id
    """), {
        "device_id": device_id,
        "fault_type": fault_type,
        "severity": severity.value,
        "message": message,
        "sensor_reading_id": sensor_reading_id
    })
    fault_id = result.scalar()
    
    return await _get_fault_by_id(db, fault_id)


async def mark_fault_cleared_by_hardware(
    db: AsyncSession,
    device_id: str,
    fault_type: str,
) -> Optional[dict]:
    """
    Move an active fault out of the active queue when the hardware clears it.
    The log stays in history and still requires a person to complete the final resolution.
    """
    result = await db.execute(text("""
        UPDATE fault_logs
        SET
            status = 'cleared_pending_close',
            cleared_at = COALESCE(cleared_at, NOW()),
            resolved_at = COALESCE(resolved_at, NOW()),
            resolved_by = COALESCE(resolved_by, 'hardware'),
            resolution_notes = CASE
                WHEN resolution_notes IS NULL OR resolution_notes = '' THEN
                    'Fault cleared by hardware/ESP32. Pending manual close from website.'
                WHEN POSITION('Fault cleared by hardware/ESP32. Pending manual close from website.' IN resolution_notes) > 0 THEN
                    resolution_notes
                ELSE
                    resolution_notes || E'\n\nFault cleared by hardware/ESP32. Pending manual close from website.'
            END
        WHERE id = (
            SELECT id
            FROM fault_logs
            WHERE device_id = :device_id
              AND fault_type = :fault_type
              AND status = 'active'
            ORDER BY detected_at DESC
            LIMIT 1
        )
        RETURNING id
    """), {"device_id": device_id, "fault_type": fault_type})
    row = result.mappings().first()
    if not row:
        return None
    return await _get_fault_by_id(db, row["id"])


# ─────────────────────────────────────────────────────────────────────────────
# Fault Context Endpoint - "Why did this fault happen?"
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/faults/{fault_id}/context")
async def get_fault_context(
    fault_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """
    Get the sensor snapshot that triggered a fault, plus a computed diagnosis.
    Returns: { fault, sensor_snapshot, diagnosis }
    """
    # 1. Fetch the fault
    fault_result = await db.execute(text("""
        SELECT id, device_id, fault_type, severity, message, detected_at, sensor_reading_id
        FROM fault_logs WHERE id = :fault_id
    """), {"fault_id": fault_id})
    fault = fault_result.mappings().first()
    
    if not fault:
        raise HTTPException(status_code=404, detail="Fault not found")
    
    fault_dict = dict(fault)
    device_id = fault_dict["device_id"]
    detected_at = fault_dict["detected_at"]
    sensor_reading_id = fault_dict.get("sensor_reading_id")
    
    # 2. Get sensor snapshot (from stored ID or fallback query)
    snapshot = None
    if sensor_reading_id:
        snap_result = await db.execute(text("""
            SELECT * FROM sensor_readings WHERE id = :id
        """), {"id": sensor_reading_id})
        snapshot = snap_result.mappings().first()
    
    # Fallback: find closest reading before fault
    if not snapshot:
        fallback_result = await db.execute(text("""
            SELECT * FROM sensor_readings 
            WHERE device_id = :device_id AND ts <= :detected_at
            ORDER BY ts DESC LIMIT 1
        """), {"device_id": device_id, "detected_at": detected_at})
        snapshot = fallback_result.mappings().first()
    
    sensor_snapshot = dict(snapshot) if snapshot else {}
    
    # 3. Compute diagnosis
    diagnosis = _compute_diagnosis(fault_dict["fault_type"], sensor_snapshot)
    
    return {
        "fault": fault_dict,
        "sensor_snapshot": sensor_snapshot,
        "diagnosis": diagnosis
    }


def _compute_diagnosis(fault_type: str, snapshot: dict) -> dict:
    """Compute a plain-English diagnosis from fault type and sensor values."""
    
    # Protection thresholds (these should match what's in data.py)
    PROTECTION_CONFIG = {
        "max_current": 10.0,
        "max_temp": 80.0,
        "min_rpm": 100.0,
        "overvoltage": 260.0,
        "undervoltage": 180.0,
        "vibration_threshold": 2.0
    }
    
    diagnosis = {
        "triggered_by": fault_type,
        "actual_value": None,
        "threshold_value": None,
        "excess_pct": None,
        "human_explanation": "",
        "contributing_factors": [],
        "recommended_actions": []
    }
    
    if not snapshot:
        diagnosis["human_explanation"] = "No sensor data available at time of fault."
        diagnosis["recommended_actions"] = ["Check device data logging", "Verify sensor connectivity"]
        return diagnosis
    
    if fault_type == "overcurrent":
        current = snapshot.get("current", 0)
        threshold = PROTECTION_CONFIG["max_current"]
        diagnosis["actual_value"] = current
        diagnosis["threshold_value"] = threshold
        if current > threshold:
            excess = ((current - threshold) / threshold) * 100
            diagnosis["excess_pct"] = round(excess, 1)
            diagnosis["human_explanation"] = f"Motor drew {current:.1f} A, which is {excess:.0f}% above the {threshold:.1f} A limit."
        diagnosis["contributing_factors"] = ["High mechanical load", "Possible bearing friction", "Voltage sag"]
        diagnosis["recommended_actions"] = ["Inspect motor load", "Check for mechanical blockage", "Verify power supply stability"]
    
    elif fault_type == "overtemp":
        temp1 = snapshot.get("temp1", 0)
        temp2 = snapshot.get("temp2", 0)
        max_temp = max(temp1, temp2)
        threshold = PROTECTION_CONFIG["max_temp"]
        diagnosis["actual_value"] = max_temp
        diagnosis["threshold_value"] = threshold
        if max_temp > threshold:
            excess = ((max_temp - threshold) / threshold) * 100
            diagnosis["excess_pct"] = round(excess, 1)
            diagnosis["human_explanation"] = f"Motor temperature reached {max_temp:.1f}°C, which is {excess:.0f}% above the {threshold:.1f}°C limit."
        diagnosis["contributing_factors"] = ["Inadequate cooling", "High ambient temperature", "Excessive load duration"]
        diagnosis["recommended_actions"] = ["Check cooling fans", "Inspect heat sink", "Reduce load cycles", "Verify ambient temperature"]
    
    elif fault_type == "stall":
        rpm = snapshot.get("rpm", 0)
        current = snapshot.get("current", 0)
        threshold = PROTECTION_CONFIG["min_rpm"]
        diagnosis["actual_value"] = rpm
        diagnosis["threshold_value"] = threshold
        diagnosis["human_explanation"] = f"Motor stalled at {rpm} RPM (minimum: {threshold} RPM). Current draw was {current:.1f} A."
        diagnosis["contributing_factors"] = ["Mechanical blockage", "Insufficient voltage", "Motor winding failure"]
        diagnosis["recommended_actions"] = ["Check for mechanical obstruction", "Verify voltage supply", "Inspect motor windings"]
    
    elif fault_type == "overvoltage":
        voltage = snapshot.get("voltage", 0)
        threshold = PROTECTION_CONFIG["overvoltage"]
        diagnosis["actual_value"] = voltage
        diagnosis["threshold_value"] = threshold
        if voltage > threshold:
            excess = ((voltage - threshold) / threshold) * 100
            diagnosis["excess_pct"] = round(excess, 1)
            diagnosis["human_explanation"] = f"Supply voltage was {voltage:.1f}V, which is {excess:.0f}% above the {threshold:.1f}V limit."
        diagnosis["contributing_factors"] = ["Power grid fluctuation", "Faulty voltage regulator"]
        diagnosis["recommended_actions"] = ["Check power regulator", "Monitor grid stability"]
    
    elif fault_type == "undervoltage":
        voltage = snapshot.get("voltage", 0)
        threshold = PROTECTION_CONFIG["undervoltage"]
        diagnosis["actual_value"] = voltage
        diagnosis["threshold_value"] = threshold
        if voltage < threshold:
            deficit = ((threshold - voltage) / threshold) * 100
            diagnosis["excess_pct"] = -round(deficit, 1)  # Negative to indicate under
            diagnosis["human_explanation"] = f"Supply voltage was {voltage:.1f}V, which is {deficit:.0f}% below the {threshold:.1f}V minimum."
        diagnosis["contributing_factors"] = ["Power supply overload", "Long cable runs", "Grid undervoltage"]
        diagnosis["recommended_actions"] = ["Check power supply capacity", "Verify cable gauge", "Check for voltage drop"]
    
    elif fault_type == "vibration":
        accel_x = snapshot.get("accel_x", 0)
        accel_y = snapshot.get("accel_y", 0)
        accel_z = snapshot.get("accel_z", 0)
        magnitude = (accel_x**2 + accel_y**2 + accel_z**2) ** 0.5
        threshold = PROTECTION_CONFIG["vibration_threshold"]
        diagnosis["actual_value"] = round(magnitude, 2)
        diagnosis["threshold_value"] = threshold
        if magnitude > threshold:
            excess = ((magnitude - threshold) / threshold) * 100
            diagnosis["excess_pct"] = round(excess, 1)
            diagnosis["human_explanation"] = f"Vibration magnitude was {magnitude:.2f}g, which is {excess:.0f}% above the {threshold:.1f}g limit."
        diagnosis["contributing_factors"] = ["Unbalanced rotor", "Worn bearings", "Loose mounting"]
        diagnosis["recommended_actions"] = ["Check bearing condition", "Verify rotor balance", "Inspect mountings"]
    
    else:
        diagnosis["human_explanation"] = f"Fault type '{fault_type}' detected. No detailed diagnosis available."
        diagnosis["recommended_actions"] = ["Review fault logs manually"]
    
    return diagnosis


# ── GET /faults/{device_id}/export ───────────────────────────────────────────
@router.get("/faults/{device_id}/export")
async def export_faults_csv(
    device_id: str,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Export fault logs as a CSV file."""
    count_query = "SELECT COUNT(*) FROM fault_logs f WHERE f.device_id = :device_id"
    query = """
        SELECT 
            f.id, f.device_id, f.fault_type, f.severity,
            f.status, f.message, f.detected_at, f.resolved_at, f.resolved_by,
            f.root_cause, f.actions_taken, f.parts_replaced, f.resolution_notes,
            f.sensor_reading_id
        FROM fault_logs f
        WHERE f.device_id = :device_id
    """
    params = {"device_id": device_id}
    
    if start_date:
        query += " AND f.detected_at >= :start_date"
        count_query += " AND f.detected_at >= :start_date"
        params["start_date"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        query += " AND f.detected_at <= :end_date"
        count_query += " AND f.detected_at <= :end_date"
        params["end_date"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
    query += " ORDER BY f.detected_at ASC"

    count_result = await db.execute(text(count_query), params)
    if count_result.scalar() == 0:
        raise HTTPException(status_code=404, detail="No fault logs found for the selected date range")

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
        "Content-Disposition": f"attachment; filename=fault_logs_{device_id}.csv"
    }
    return StreamingResponse(iter_csv(), media_type="text/csv", headers=headers)
