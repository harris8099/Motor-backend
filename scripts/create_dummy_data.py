import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import AsyncSessionLocal, settings

# Database connection settings
DATABASE_URL = settings.database_url

async def create_dummy_data():
    """Create dummy sensor data, fault events, and predictions for testing"""
    
    async with AsyncSessionLocal() as db:
        print("Creating dummy data for testing ML predictions...")
        
        # Devices to create data for
        devices = [
            {"id": "esp32-001", "name": "Main Motor A"},
            {"id": "esp32-002", "name": "Secondary Motor B"},
            {"id": "esp32-003", "name": "Backup Motor C"},
            {"id": "motor-004", "name": "Production Motor D"},
            {"id": "motor-005", "name": "Test Motor E"}
        ]
        
        # Ensure devices exist and are active with recent timestamps
        for device in devices:
            await db.execute(text("""
                INSERT INTO devices (id, name, is_active, created_at, updated_at, last_seen_at, location, firmware_version)
                VALUES (:id, :name, TRUE, NOW() - INTERVAL '7 days', NOW(), NOW() - INTERVAL '5 minutes', 'Factory Floor', 'v1.2.3')
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    is_active = TRUE,
                    last_seen_at = NOW() - INTERVAL '5 minutes',
                    updated_at = NOW()
            """), device)
        
        await db.commit()
        print("✓ Devices ensured")
        
        # Clear existing dummy data to avoid duplicates
        await db.execute(text("DELETE FROM sensor_readings WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'"))
        await db.execute(text("DELETE FROM fault_events WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'"))
        await db.execute(text("DELETE FROM predictions WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'"))
        await db.commit()
        print("✓ Cleared existing dummy data")
        
        # Generate sensor readings for the last 48 hours
        now = datetime.now(timezone.utc)
        readings_per_device = 500  # About 4 hours of data at 30-second intervals
        
        for device in devices:
            device_id = device["id"]
            print(f"Generating data for {device_id}...")
            
            # Different baseline characteristics for each device
            base_rpm = random.choice([1450, 1500, 1550, 1600, 1750])
            base_voltage = random.choice([220, 230, 240, 250])
            base_temp = random.choice([45, 55, 65, 75])
            
            for i in range(readings_per_device):
                # Generate timestamp (going backwards from now)
                timestamp = now - timedelta(minutes=i*0.5)  # 30-second intervals
                
                # Simulate realistic motor behavior with some noise
                motor_running = random.random() > 0.1  # 90% uptime
                rpm = base_rpm + random.randint(-100, 100) if motor_running else 0
                uptime = i * 30 if motor_running else random.randint(0, 86400)
                
                # Power measurements with realistic variations
                voltage = base_voltage + random.uniform(-5, 5)
                current = random.uniform(8, 15) if motor_running else 0.5
                power = voltage * current / 1000 if motor_running else 0  # kW
                power_factor = random.uniform(0.85, 0.95) if motor_running else 0
                energy = uptime * power / 3600 if motor_running else 0  # kWh
                frequency = 50 + random.uniform(-0.5, 0.5)
                
                # Temperature sensors
                temp1 = base_temp + random.uniform(-5, 10) if motor_running else 25
                temp2 = base_temp + random.uniform(-3, 8) if motor_running else 24
                
                # Vibration data
                accel_x = random.uniform(-2, 2) if motor_running else 0
                accel_y = random.uniform(-2, 2) if motor_running else 0
                accel_z = random.uniform(-2, 2) + (9.8 if motor_running else 0)  # Include gravity
                tap_detected = random.random() < 0.02  # 2% chance of tap
                
                # Fault conditions (rare events)
                fault_overcurrent = random.random() < 0.005 and current > 14
                fault_overtemp = random.random() < 0.003 and temp1 > 80
                fault_stall = random.random() < 0.002 and rpm < 100 and motor_running
                fault_vibration = random.random() < 0.004 and abs(accel_x) > 1.5
                fault_overvoltage = random.random() < 0.001 and voltage > 255
                fault_undervoltage = random.random() < 0.002 and voltage < 210
                
                # Protection settings
                prot_max_current = 15.0
                prot_max_temp = 85.0
                prot_min_rpm = 1200
                prot_overvoltage = 260.0
                prot_undervoltage = 200.0
                prot_stall_current = 18.0
                prot_startup_grace = 5000
                prot_fault_trip_count = 3
                prot_vibration_ack_grace = 10000
                
                # Maintenance data
                maint_total_hours = uptime / 3600
                maint_hours_limit = 8760  # 1 year
                maint_total_seconds = uptime
                maint_limit_seconds = maint_hours_limit * 3600
                
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
                    "motor_running": motor_running,
                    "rpm": rpm,
                    "pulse": rpm // 60 if rpm > 0 else 0,
                    "uptime_seconds": uptime,
                    "voltage": voltage,
                    "current": current,
                    "power": power,
                    "power_factor": power_factor,
                    "energy": energy,
                    "frequency": frequency,
                    "temp1": temp1,
                    "temp2": temp2,
                    "accel_x": accel_x,
                    "accel_y": accel_y,
                    "accel_z": accel_z,
                    "tap_detected": tap_detected,
                    "fault_overcurrent": fault_overcurrent,
                    "fault_overtemp": fault_overtemp,
                    "fault_stall": fault_stall,
                    "fault_vibration": fault_vibration,
                    "fault_overvoltage": fault_overvoltage,
                    "fault_undervoltage": fault_undervoltage,
                    "prot_max_current": prot_max_current,
                    "prot_max_temp": prot_max_temp,
                    "prot_min_rpm": prot_min_rpm,
                    "prot_overvoltage": prot_overvoltage,
                    "prot_undervoltage": prot_undervoltage,
                    "prot_stall_current": prot_stall_current,
                    "prot_startup_grace": prot_startup_grace,
                    "prot_fault_trip_count": prot_fault_trip_count,
                    "prot_vibration_ack_grace": prot_vibration_ack_grace,
                    "maint_next_time": "2024-12-31T23:59:59Z",
                    "maint_total_hours": maint_total_hours,
                    "maint_hours_limit": maint_hours_limit,
                    "maint_total_seconds": maint_total_seconds,
                    "maint_limit_seconds": maint_limit_seconds
                })
                
                # Create fault events when faults occur
                if fault_overcurrent:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'overcurrent', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": current})
                
                if fault_overtemp:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'overtemp', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": temp1})
                
                if fault_stall:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'stall', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": rpm})
                
                if fault_vibration:
                    await db.execute(text("""
                        INSERT INTO fault_events (device_id, ts, fault_type, value)
                        VALUES (:device_id, :ts, 'vibration', :value)
                    """), {"device_id": device_id, "ts": timestamp, "value": accel_x})
            
            await db.commit()
        
        print(f"✓ Generated {readings_per_device * len(devices)} sensor readings")
        
        # Generate ML predictions for each device
        prediction_types = [
            "bearing_fault", "overheating", "stall_risk", "power_anomaly", 
            "vibration_anomaly", "efficiency_drop", "maintenance_due"
        ]
        
        for device in devices:
            device_id = device["id"]
            print(f"Generating predictions for {device_id}...")
            
            # Generate 10-20 predictions per device with varying confidence levels
            num_predictions = random.randint(10, 20)
            
            for i in range(num_predictions):
                prediction_time = now - timedelta(hours=random.randint(1, 48))
                prediction_type = random.choice(prediction_types)
                
                # Vary confidence and severity based on device
                if device_id == "esp32-001":  # Main motor - more critical
                    confidence = random.uniform(0.6, 0.95)
                    severity = random.choice(["medium", "high"]) if confidence > 0.8 else "low"
                elif device_id == "motor-005":  # Test motor - more issues
                    confidence = random.uniform(0.4, 0.9)
                    severity = random.choice(["low", "medium", "high"])
                else:
                    confidence = random.uniform(0.3, 0.8)
                    severity = random.choice(["low", "medium"])
                
                # Generate realistic prediction details
                if prediction_type == "bearing_fault":
                    details = {
                        "vibration_increase": f"{random.uniform(1.2, 3.5):.2f}x",
                        "frequency_peak": random.randint(50, 200),
                        "estimated_rul_days": random.randint(30, 180),
                        "affected_bearing": random.choice(["input", "output"])
                    }
                elif prediction_type == "overheating":
                    details = {
                        "temp_trend": "increasing",
                        "current_temp": random.uniform(75, 95),
                        "max_safe_temp": 85,
                        "cooling_efficiency": random.uniform(0.6, 0.9),
                        "estimated_rul_hours": random.randint(48, 240)
                    }
                elif prediction_type == "stall_risk":
                    details = {
                        "rpm_variance": f"{random.uniform(5, 15):.1f}%",
                        "load_factor": random.uniform(0.8, 1.2),
                        "torque_margin": random.uniform(5, 20),
                        "risk_probability": confidence
                    }
                elif prediction_type == "power_anomaly":
                    details = {
                        "power_factor": random.uniform(0.7, 0.9),
                        "current_imbalance": f"{random.uniform(2, 8):.1f}%",
                        "harmonics_detected": random.choice([True, False]),
                        "efficiency_loss": f"{random.uniform(5, 15):.1f}%"
                    }
                elif prediction_type == "vibration_anomaly":
                    details = {
                        "overall_vibration": random.uniform(2, 8),
                        "peak_frequency": random.randint(25, 500),
                        "spectral_peaks": random.randint(3, 8),
                        "severity_score": confidence
                    }
                elif prediction_type == "efficiency_drop":
                    details = {
                        "current_efficiency": random.uniform(0.75, 0.92),
                        "baseline_efficiency": random.uniform(0.90, 0.95),
                        "power_loss_kw": random.uniform(0.5, 2.5),
                        "annual_cost_impact": random.uniform(100, 800)
                    }
                else:  # maintenance_due
                    details = {
                        "running_hours": random.uniform(7000, 8600),
                        "maintenance_interval": 8760,
                        "overdue_by_hours": random.uniform(0, 200),
                        "recommended_actions": ["oil_change", "bearing_inspection", "belt_check"]
                    }
                
                await db.execute(text("""
                    INSERT INTO predictions (device_id, ts, prediction_type, confidence, severity, details)
                    VALUES (:device_id, :ts, :prediction_type, :confidence, :severity, :details)
                """), {
                    "device_id": device_id,
                    "ts": prediction_time,
                    "prediction_type": prediction_type,
                    "confidence": confidence,
                    "severity": severity,
                    "details": json.dumps(details)
                })
            
            await db.commit()
        
        print(f"✓ Generated {num_predictions * len(devices)} ML predictions")
        
        # Update device statistics
        stats = await db.execute(text("""
            SELECT 
                device_id,
                COUNT(*) as total_readings,
                COUNT(CASE WHEN motor_running = TRUE THEN 1 END) as running_readings,
                AVG(CASE WHEN motor_running = TRUE THEN rpm END) as avg_rpm,
                MAX(temp1) as max_temp,
                COUNT(CASE WHEN fault_overcurrent = TRUE OR fault_overtemp = TRUE OR fault_stall = TRUE THEN 1 END) as fault_count
            FROM sensor_readings 
            WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'
            GROUP BY device_id
        """))
        
        for stat in stats.mappings():
            print(f"Device {stat['device_id']}: {stat['total_readings']} readings, "
                  f"{stat['running_readings']} running, avg RPM: {stat['avg_rpm']:.0f}, "
                  f"max temp: {stat['max_temp']:.1f}°C, faults: {stat['fault_count']}")
        
        print("\n✅ Dummy data creation completed!")
        print("📊 Database now contains:")
        print(f"   • {len(devices)} active devices")
        print(f"   • {readings_per_device * len(devices)} sensor readings")
        print(f"   • {num_predictions * len(devices)} ML predictions")
        print(f"   • Various fault events for testing")
        print("\n🌐 You can now test the ML predictions on the website!")

if __name__ == "__main__":
    asyncio.run(create_dummy_data())
