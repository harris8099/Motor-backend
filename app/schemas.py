from pydantic import BaseModel
from typing import Optional

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
