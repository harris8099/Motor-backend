#!/usr/bin/env python3
"""
Seed script to add realistic industrial motor devices with sensor data.
Based on real-world motor specifications from industrial applications.
"""
import asyncio
import sys
import random
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.database import settings

# Fix database URL for asyncpg
url = settings.database_url
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
url = url.split("?")[0]

engine = create_async_engine(url, connect_args={"ssl": "require"})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Realistic industrial motors based on actual specifications
# Sources: NEMA standards, typical manufacturing equipment
SAMPLE_DEVICES = [
    {
        "id": "esp32-001",
        "name": "Conveyor Motor - Line 1",
        "description": "5HP 3-phase induction motor, 1750 RPM, 230/460V. Drives main assembly conveyor.",
        "location": "Assembly Line 1 - Station A",
        "motor_specs": {
            "horsepower": 5,
            "rated_rpm": 1750,
            "voltage": 230,
            "current": 13.0,
            "poles": 4,
            "efficiency": 0.89,
            "power_factor": 0.85,
            "frame_size": "184T"
        }
    },
    {
        "id": "esp32-002",
        "name": "Conveyor Motor - Line 2",
        "description": "3HP 3-phase motor, 1725 RPM, 208-230/460V. Secondary packaging conveyor.",
        "location": "Assembly Line 2 - Station B",
        "motor_specs": {
            "horsepower": 3,
            "rated_rpm": 1725,
            "voltage": 230,
            "current": 8.8,
            "poles": 4,
            "efficiency": 0.88,
            "power_factor": 0.82,
            "frame_size": "182T"
        }
    },
    {
        "id": "esp32-003",
        "name": "Cooling Pump Motor",
        "description": "2HP TEFC motor, 3450 RPM, 115/230V single-phase. High-speed circulation pump.",
        "location": "Cooling Tower - Utility Room",
        "motor_specs": {
            "horsepower": 2,
            "rated_rpm": 3450,
            "voltage": 230,
            "current": 12.0,
            "poles": 2,
            "efficiency": 0.86,
            "power_factor": 0.75,
            "frame_size": "145T"
        }
    },
    {
        "id": "esp32-004",
        "name": "HVAC Supply Fan Motor",
        "description": "10HP 3-phase motor, 1180 RPM, 460V. Low-speed high-torque for air handling.",
        "location": "Roof HVAC Unit 1",
        "motor_specs": {
            "horsepower": 10,
            "rated_rpm": 1180,
            "voltage": 460,
            "current": 14.0,
            "poles": 6,
            "efficiency": 0.91,
            "power_factor": 0.88,
            "frame_size": "215T"
        }
    },
    {
        "id": "esp32-005",
        "name": "Hydraulic Pump Motor",
        "description": "7.5HP 3-phase motor, 1760 RPM, 230/460V. Powers hydraulic press system.",
        "location": "Hydraulic Station - Press Area",
        "motor_specs": {
            "horsepower": 7.5,
            "rated_rpm": 1760,
            "voltage": 460,
            "current": 11.0,
            "poles": 4,
            "efficiency": 0.90,
            "power_factor": 0.86,
            "frame_size": "213T"
        }
    },
    {
        "id": "esp32-006",
        "name": "Agitator Mixer Motor",
        "description": "1.5HP 3-phase motor, 850 RPM, 230/460V. Slow-speed high-torque for mixing tank.",
        "location": "Chemical Processing - Mixing Bay",
        "motor_specs": {
            "horsepower": 1.5,
            "rated_rpm": 850,
            "voltage": 230,
            "current": 4.8,
            "poles": 8,
            "efficiency": 0.84,
            "power_factor": 0.80,
            "frame_size": "145T"
        }
    },
    {
        "id": "esp32-007",
        "name": "Compressor Motor",
        "description": "15HP 3-phase motor, 1765 RPM, 460V. Air compressor for pneumatics.",
        "location": "Compressor Room",
        "motor_specs": {
            "horsepower": 15,
            "rated_rpm": 1765,
            "voltage": 460,
            "current": 19.5,
            "poles": 4,
            "efficiency": 0.92,
            "power_factor": 0.89,
            "frame_size": "254T"
        }
    },
    {
        "id": "esp32-008",
        "name": "Test Bench Motor",
        "description": "0.5HP single-phase motor, 1725 RPM, 115/230V. Variable load test unit.",
        "location": "R&D Lab - Test Bench 3",
        "motor_specs": {
            "horsepower": 0.5,
            "rated_rpm": 1725,
            "voltage": 115,
            "current": 7.2,
            "poles": 4,
            "efficiency": 0.78,
            "power_factor": 0.70,
            "frame_size": "56"
        }
    },
]

SAMPLE_DEVICE_IDS = [device["id"] for device in SAMPLE_DEVICES]


def generate_realistic_sensor_data(specs, timestamp, load_factor=0.85):
    """
    Generate realistic sensor readings based on actual motor specifications.
    Based on NEMA standards and typical industrial motor performance curves.
    """
    hp = specs["horsepower"]
    rated_rpm = specs["rated_rpm"]
    voltage = specs["voltage"]
    rated_current = specs["current"]
    efficiency = specs["efficiency"]
    pf = specs["power_factor"]
    
    # Motor is running 90% of the time (realistic uptime)
    motor_running = random.random() > 0.1
    
    if motor_running:
        # RPM varies slightly based on load (slip typically 2-5%)
        slip_percent = random.uniform(0.02, 0.05) * load_factor
        rpm = int(rated_rpm * (1 - slip_percent) + random.randint(-20, 20))
        
        # Current varies with load (proportional to load factor)
        current_variation = random.uniform(-0.15, 0.15)
        current = rated_current * load_factor * (1 + current_variation)
        
        # Voltage typically within +/- 5% of nominal
        voltage_actual = voltage * random.uniform(0.95, 1.05)
        
        # Power calculation: P = V * I * PF * sqrt(3) / 1000 for 3-phase
        if specs.get("poles", 4) in [2, 4, 6, 8]:  # 3-phase
            power_kw = (voltage_actual * current * pf * 1.732) / 1000
        else:
            power_kw = (voltage_actual * current * pf) / 1000  # single-phase
        
        # Power factor varies slightly with load
        power_factor = pf * random.uniform(0.92, 1.08)
        
        # Energy accumulates based on runtime
        uptime = random.randint(0, 86400)  # seconds (0-24 hours)
        energy = uptime * power_kw / 3600
        
        # Frequency (50Hz standard with small variations)
        frequency = 50 + random.uniform(-0.3, 0.3)
        
        # Temperature based on load (typical: 40-80°C at full load)
        temp_rise = 20 + (load_factor * 35)  # Temperature rise above ambient
        base_temp = 25  # Ambient
        temp1 = base_temp + temp_rise + random.uniform(-3, 5)
        temp2 = temp1 - random.uniform(2, 8)  # Second sensor slightly cooler
        
        # Vibration levels (typical industrial motors: 2-7 mm/s RMS)
        vibration_base = random.uniform(2.0, 4.0)
        vibration_variation = random.uniform(-1.5, 2.0)
        accel_x = (vibration_base + vibration_variation) * random.uniform(-1, 1)
        accel_y = (vibration_base + vibration_variation) * random.uniform(-1, 1)
        accel_z = 9.8 + (vibration_base * random.uniform(-0.5, 0.5))  # Gravity + vibration
        
    else:
        # Motor stopped - minimal readings
        rpm = 0
        current = random.uniform(0.1, 0.5)  # Residual/noise
        voltage_actual = voltage * random.uniform(0.98, 1.02)
        power_kw = 0
        power_factor = random.uniform(0.1, 0.3)
        uptime = random.randint(0, 300)  # Short downtime
        energy = 0
        frequency = 0
        temp1 = random.uniform(22, 28)  # Ambient temp
        temp2 = temp1 - random.uniform(0, 2)
        accel_x = random.uniform(-0.5, 0.5)
        accel_y = random.uniform(-0.5, 0.5)
        accel_z = 9.8  # Just gravity
    
    # Protection settings (standard industrial values)
    prot_max_current = rated_current * 1.25  # 125% overload trip
    prot_max_temp = 85.0  # Thermal protection
    prot_min_rpm = rated_rpm * 0.3  # Stall detection at 30% of rated
    prot_overvoltage = voltage * 1.15
    prot_undervoltage = voltage * 0.85
    prot_stall_current = rated_current * 1.5
    
    # Maintenance tracking
    maint_hours_limit = 8760  # 1 year typical
    maint_total_hours = uptime / 3600
    
    return {
        "motor_running": motor_running,
        "rpm": max(0, rpm),
        "pulse": max(0, rpm // 60) if motor_running else 0,
        "uptime_seconds": uptime,
        "voltage": round(voltage_actual, 2),
        "current": round(current, 3),
        "power": round(power_kw, 3),
        "power_factor": round(power_factor, 3),
        "energy": round(energy, 6),
        "frequency": round(frequency, 2),
        "temp1": round(temp1, 1),
        "temp2": round(temp2, 1),
        "accel_x": round(accel_x, 3),
        "accel_y": round(accel_y, 3),
        "accel_z": round(accel_z, 3),
        "tap_detected": random.random() < 0.02,
        "prot_max_current": prot_max_current,
        "prot_max_temp": prot_max_temp,
        "prot_min_rpm": prot_min_rpm,
        "prot_overvoltage": prot_overvoltage,
        "prot_undervoltage": prot_undervoltage,
        "prot_stall_current": prot_stall_current,
        "prot_startup_grace": 5000,
        "prot_fault_trip_count": 3,
        "prot_vibration_ack_grace": 10000,
        "maint_total_hours": round(maint_total_hours, 2),
        "maint_hours_limit": maint_hours_limit,
        "maint_total_seconds": uptime,
        "maint_limit_seconds": maint_hours_limit * 3600,
        "maint_next_time": "2024-12-31T23:59:59Z",
    }


async def seed_devices():
    """Add realistic industrial motor devices with sensor data to the database."""
    async with AsyncSessionLocal() as db:
        print("Seeding realistic industrial motor devices...")
        print("=" * 60)
        
        # Track created devices
        devices_created = 0
        devices_updated = 0
        
        for device in SAMPLE_DEVICES:
            device_id = device["id"]
            specs = device["motor_specs"]
            
            # Check if device already exists
            result = await db.execute(
                text("SELECT id, is_active FROM devices WHERE id = :id"),
                {"id": device_id}
            )
            existing = result.mappings().first()
            
            device_data = {
                "id": device_id,
                "name": device["name"],
                "description": device["description"],
                "location": device["location"],
                "is_active": True,
                "firmware_version": "v1.2.3",
                "last_seen_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 30))
            }
            
            if existing:
                print(f"Updating device {device_id}...")
                await db.execute(text("""
                    UPDATE devices SET
                        name = :name,
                        description = :description,
                        location = :location,
                        is_active = :is_active,
                        firmware_version = :firmware_version,
                        last_seen_at = :last_seen_at,
                        updated_at = NOW()
                    WHERE id = :id
                """), device_data)
                devices_updated += 1
            else:
                print(f"Creating device {device_id}...")
                print(f"   Location: {device['location']}")
                print(f"   Motor: {specs['horsepower']}HP @ {specs['rated_rpm']} RPM, {specs['voltage']}V")
                await db.execute(text("""
                    INSERT INTO devices (id, name, description, location, is_active, 
                                        firmware_version, last_seen_at, created_at, updated_at)
                    VALUES (:id, :name, :description, :location, :is_active,
                            :firmware_version, :last_seen_at, NOW(), NOW())
                """), device_data)
                devices_created += 1
        
        await db.commit()

        # Reset generated seed data so reruns remain deterministic and don't skip partial data.
        id_params = {f"id_{index}": device_id for index, device_id in enumerate(SAMPLE_DEVICE_IDS)}
        id_placeholders = ", ".join(f":id_{index}" for index in range(len(SAMPLE_DEVICE_IDS)))

        await db.execute(text(f"DELETE FROM fault_events WHERE device_id IN ({id_placeholders})"), id_params)
        await db.execute(text(f"DELETE FROM sensor_readings WHERE device_id IN ({id_placeholders})"), id_params)
        await db.commit()
        
        # Generate realistic sensor readings for each device
        print("\nGenerating realistic sensor data...")
        print("-" * 60)
        
        now = datetime.now(timezone.utc)
        total_readings = 0
        
        for device in SAMPLE_DEVICES:
            device_id = device["id"]
            specs = device["motor_specs"]

            # Generate 100 readings per device (spanning last 24 hours)
            readings_count = 100
            
            for i in range(readings_count):
                # Stagger timestamps (every ~15 minutes)
                timestamp = now - timedelta(minutes=i * 15)
                
                # Vary load factor over time (simulates shift changes)
                load_factor = random.choice([0.6, 0.75, 0.85, 0.95, 0.9])
                
                # Generate sensor data based on motor specs
                data = generate_realistic_sensor_data(specs, timestamp, load_factor)
                
                # Determine faults based on conditions
                fault_overcurrent = data["current"] > specs["current"] * 1.2
                fault_overtemp = data["temp1"] > 80
                fault_stall = data["motor_running"] and data["rpm"] < specs["rated_rpm"] * 0.3
                fault_vibration = abs(data["accel_x"]) > 6.0 or abs(data["accel_y"]) > 6.0
                fault_overvoltage = data["voltage"] > specs["voltage"] * 1.1
                fault_undervoltage = data["voltage"] < specs["voltage"] * 0.9
                
                # Insert sensor reading
                await db.execute(text("""
                    INSERT INTO sensor_readings (
                        device_id, ts, motor_running, rpm, pulse, uptime_seconds,
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
                        :device_id, :ts, :motor_running, :rpm, :pulse, :uptime_seconds,
                        :voltage, :current, :power, :power_factor, :energy, :frequency,
                        :temp1, :temp2, :accel_x, :accel_y, :accel_z, :tap_detected,
                        :fault_overcurrent, :fault_overtemp, :fault_stall,
                        :fault_vibration, :fault_overvoltage, :fault_undervoltage,
                        :prot_max_current, :prot_max_temp, :prot_min_rpm,
                        :prot_overvoltage, :prot_undervoltage, :prot_stall_current,
                        :prot_startup_grace, :prot_fault_trip_count, :prot_vibration_ack_grace,
                        :maint_next_time, :maint_total_hours, :maint_hours_limit,
                        :maint_total_seconds, :maint_limit_seconds
                    )
                """), {
                    "device_id": device_id,
                    "ts": timestamp,
                    **data,
                    "fault_overcurrent": fault_overcurrent,
                    "fault_overtemp": fault_overtemp,
                    "fault_stall": fault_stall,
                    "fault_vibration": fault_vibration,
                    "fault_overvoltage": fault_overvoltage,
                    "fault_undervoltage": fault_undervoltage,
                })
                
                # Create fault events when they occur
                if fault_overcurrent:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'overcurrent', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": data["current"]})
                
                if fault_overtemp:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'overtemp', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": data["temp1"]})
                
                if fault_stall:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'stall', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": data["rpm"]})
            
            await db.commit()
            total_readings += readings_count
            print(f"[OK] {device_id}: {readings_count} readings generated")
        
        # Show summary
        print("\n" + "=" * 60)
        print("[OK] Seeding completed!")
        print(f"   Devices created: {devices_created}")
        print(f"   Devices updated: {devices_updated}")
        print(f"   Total sensor readings: {total_readings}")
        print(f"   Data spans: Last 24 hours")
        print("\nDevice Summary:")
        print("-" * 60)
        
        for device in SAMPLE_DEVICES:
            specs = device["motor_specs"]
            print(f"- {device['id']}: {device['name']}")
            print(f"   {specs['horsepower']}HP | {specs['rated_rpm']} RPM | {specs['voltage']}V | {specs['current']}A")
            print(f"   Location: {device['location']}")
            print()


if __name__ == "__main__":
    asyncio.run(seed_devices())
