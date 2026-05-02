from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional


def _validate_iso8601_with_timezone(value: str) -> str:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Datetime must include timezone offset")
    return value

class MotorData(BaseModel):
    running: bool
    rpm: int
    pulse: int
    uptime: int

class PowerData(BaseModel):
    voltage: float
    current: float
    power: float
    powerFactor: float
    energy: float
    frequency: float

class TemperatureData(BaseModel):
    t1: float
    t2: float

class VibrationData(BaseModel):
    x: float
    y: float
    z: float
    tap: bool

class FaultsData(BaseModel):
    overcurrent: bool
    overtemp: bool
    stall: bool
    vibration: bool
    overvoltage: bool
    undervoltage: bool

class ProtectionData(BaseModel):
    maxCurrentA: float
    maxTempC: float
    minRpm: float
    overvoltageV: float
    undervoltageV: float
    stallCurrentA: float
    startupGraceMs: int
    faultTripCount: int
    vibrationAckGraceMs: int
    tapThresholdMg: Optional[int] = None   # mg; 62–16000
    tapDurationUs:  Optional[int] = None   # µs; 625–160000

class MaintenanceData(BaseModel):
    nextMaintenanceTime: str
    totalLifeCycleHours: float
    maintenanceHoursLimit: float
    totalLifeCycleSeconds: int
    maintenanceHoursLimitSeconds: int

class SensorPayload(BaseModel):
    deviceId: Optional[str] = "unknown_device"
    timestamp_ms: Optional[int] = 0
    uptime: int
    motor: MotorData
    power: PowerData
    temperature: TemperatureData
    vibration: VibrationData
    faults: FaultsData
    protection: ProtectionData
    maintenance: MaintenanceData


class AckFaultsCommand(BaseModel):
    faults: list[str] = Field(default_factory=list)

    @field_validator("faults")
    @classmethod
    def validate_faults(cls, faults: list[str]) -> list[str]:
        allowed = {
            "overcurrent",
            "overtemp",
            "stall",
            "vibration",
            "overvoltage",
            "undervoltage",
        }
        invalid = [fault for fault in faults if fault not in allowed]
        if invalid:
            raise ValueError(f"Invalid faults: {invalid}")
        return faults


class SetProtectionCommand(BaseModel):
    maxCurrentA: Optional[float] = Field(None, ge=0, le=100)
    maxTempC: Optional[float] = Field(None, ge=0, le=200)
    minRpm: Optional[int] = Field(None, ge=0, le=10000)
    overvoltageV: Optional[float] = Field(None, ge=0, le=500)
    undervoltageV: Optional[float] = Field(None, ge=0, le=500)
    stallCurrentA: Optional[float] = Field(None, ge=0, le=100)
    startupGraceMs: Optional[int] = Field(None, ge=0, le=60000)
    faultTripCount: Optional[int] = Field(None, ge=0, le=1000)
    vibrationAckGraceMs: Optional[int] = Field(None, ge=0, le=60000)
    tapThresholdMg: Optional[int] = Field(None, ge=62, le=16000)   # mirrors ESP32 limits
    tapDurationUs:  Optional[int] = Field(None, ge=625, le=160000) # mirrors ESP32 limits

    @model_validator(mode="after")
    def ensure_not_empty(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one protection field must be provided")
        return self


class SetMaintenanceCommand(BaseModel):
    nextMaintenanceTime: Optional[str] = None
    totalLifeCycleHours: Optional[float] = Field(None, ge=0, le=1_000_000)
    maintenanceHoursLimit: Optional[float] = Field(None, ge=0, le=1_000_000)
    totalLifeCycleSeconds: Optional[int] = Field(None, ge=0, le=2147483647)
    maintenanceHoursLimitSeconds: Optional[int] = Field(None, ge=0, le=2147483647)
    uptimeSeconds: Optional[int] = Field(None, ge=0, le=315360000)

    @field_validator("nextMaintenanceTime")
    @classmethod
    def validate_next_maintenance_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_iso8601_with_timezone(value)

    @model_validator(mode="after")
    def ensure_not_empty(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one maintenance field must be provided")
        return self


class SetRuntimeCommand(BaseModel):
    uptimeSeconds: int = Field(..., ge=0, le=315360000)


class EmptyCommand(BaseModel):
    pass
