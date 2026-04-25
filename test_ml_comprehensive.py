import asyncio
import json
from app.database import get_db
from sqlalchemy import text
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.services.ml_prediction import run_ml_predictions

async def create_test_scenario(db: AsyncSession, device_id: str):
    """Create a test scenario with data that will trigger ML predictions"""
    print(f"📝 Creating test scenario for {device_id}...")
    
    # Create problematic data that should trigger ML predictions
    test_scenarios = [
        # Normal data (baseline)
        {
            "power": 2000.0, "current": 10.0, "voltage": 230.0, "rpm": 1500,
            "temp1": 45.0, "temp2": 44.0, "accel_x": 0.5, "accel_y": 0.3, "accel_z": 2.0,
            "motor_running": True, "energy": 1.0, "uptime_seconds": 3600
        },
        # Slightly elevated temperature
        {
            "power": 2200.0, "current": 11.0, "voltage": 230.0, "rpm": 1480,
            "temp1": 65.0, "temp2": 63.0, "accel_x": 0.6, "accel_y": 0.4, "accel_z": 2.2,
            "motor_running": True, "energy": 1.2, "uptime_seconds": 7200
        },
        # High temperature trend
        {
            "power": 2400.0, "current": 12.0, "voltage": 230.0, "rpm": 1460,
            "temp1": 75.0, "temp2": 73.0, "accel_x": 0.7, "accel_y": 0.5, "accel_z": 2.5,
            "motor_running": True, "energy": 1.4, "uptime_seconds": 10800
        },
        # Anomalous vibration
        {
            "power": 2500.0, "current": 12.5, "voltage": 230.0, "rpm": 1450,
            "temp1": 78.0, "temp2": 76.0, "accel_x": 2.5, "accel_y": 1.8, "accel_z": 8.0,
            "motor_running": True, "energy": 1.5, "uptime_seconds": 14400
        },
        # High current, low RPM (stall risk)
        {
            "power": 2800.0, "current": 16.0, "voltage": 230.0, "rpm": 1100,
            "temp1": 82.0, "temp2": 80.0, "accel_x": 3.0, "accel_y": 2.2, "accel_z": 10.0,
            "motor_running": True, "energy": 1.7, "uptime_seconds": 18000
        }
    ]
    
    # Insert test data with timestamps
    for i, scenario in enumerate(test_scenarios):
        minutes_ago = (len(test_scenarios) - i) * 30
        await db.execute(text("""
            INSERT INTO sensor_readings 
            (device_id, power, current, voltage, rpm, temp1, temp2, accel_x, accel_y, accel_z, 
             motor_running, ts, energy, uptime_seconds)
            VALUES (:device_id, :power, :current, :voltage, :rpm, :temp1, :temp2, :accel_x, :accel_y, :accel_z,
                    :motor_running, NOW() - INTERVAL :minutes minutes, :energy, :uptime_seconds)
        """), {
            "device_id": device_id,
            "minutes": minutes_ago,
            **scenario
        })
    
    await db.commit()
    print(f"✅ Created {len(test_scenarios)} test data points for {device_id}")

async def test_ml_comprehensive():
    """Comprehensive test of ML prediction system"""
    async for db in get_db():
        print("🧪 Comprehensive ML-Based AI Prediction System Test...")
        
        device_id = "esp32-001"
        
        # Create test scenario
        await create_test_scenario(db, device_id)
        
        # Create problematic payload that should trigger predictions
        test_payload = SensorPayload(
            deviceId=device_id,
            motor=MotorData(
                running=True,
                rpm=1050,  # Low RPM
                pulse=24,
                uptime=20000
            ),
            uptime=20000,
            power=PowerData(
                voltage=220.0,
                current=17.5,  # High current
                power=3850.0,  # High power
                powerFactor=0.85,
                energy=8.5,
                frequency=49.5
            ),
            temperature=TemperatureData(
                t1=88.0,  # Very high temperature
                t2=86.0
            ),
            vibration=VibrationData(
                x=4.2,   # Very high vibration
                y=3.1,
                z=15.8,
                tap=False
            ),
            faults=FaultsData(
                overcurrent=False,
                overtemp=False,
                stall=False,
                vibration=False,
                overvoltage=False,
                undervoltage=False
            ),
            protection=ProtectionData(
                maxCurrentA=15.0,
                maxTempC=85.0,
                minRpm=1200,
                overvoltageV=260.0,
                undervoltageV=200.0,
                stallCurrentA=18.0,
                startupGraceMs=5000,
                faultTripCount=3,
                vibrationAckGraceMs=10000
            ),
            maintenance=MaintenanceData(
                nextMaintenanceTime="2024-12-31T23:59:59Z",
                totalLifeCycleHours=8500,
                maintenanceHoursLimit=8760,
                maintenanceHoursLimitSeconds=31536000,
                totalLifeCycleSeconds=30600000
            )
        )
        
        print(f"\n🔍 Testing with problematic payload:")
        print(f"   RPM: {test_payload.motor.rpm} (threshold: {test_payload.protection.minRpm})")
        print(f"   Current: {test_payload.power.current}A (threshold: {test_payload.protection.maxCurrentA})")
        print(f"   Temperature: {(test_payload.temperature.t1 + test_payload.temperature.t2)/2}°C (threshold: {test_payload.protection.maxTempC})")
        print(f"   Vibration: {(test_payload.vibration.x**2 + test_payload.vibration.y**2 + test_payload.vibration.z**2)**0.5:.2f}")
        
        # Run ML predictions
        predictions = await run_ml_predictions(test_payload, db)
        
        print(f"\n🤖 Generated {len(predictions)} ML-based predictions:")
        for i, pred in enumerate(predictions, 1):
            print(f"\n{i}. {pred['type'].upper().replace('_', ' ')}")
            print(f"   Confidence: {pred['confidence']:.2f}")
            print(f"   Severity: {pred['severity']}")
            
            # Format details for better readability
            details = pred['details']
            if isinstance(details, dict):
                for key, value in details.items():
                    if key == 'comment':
                        print(f"   💭 AI Comment: {value}")
                    elif key == 'risk_factors' and isinstance(value, list):
                        print(f"   Risk Factors: {', '.join(value)}")
                    elif isinstance(value, float):
                        if 'rate' in key or 'ratio' in key:
                            print(f"   {key}: {(value * 100):.1f}%")
                        elif 'time' in key and 'minutes' in key:
                            print(f"   {key}: {int(value)} min")
                        elif 'temp' in key or 'power' in key or 'current' in key or 'vibration' in key:
                            print(f"   {key}: {value:.2f}")
                        else:
                            print(f"   {key}: {value:.3f}")
                    else:
                        print(f"   {key}: {value}")
            else:
                print(f"   Details: {details}")
        
        # Store predictions in database for testing
        print(f"\n💾 Storing ML predictions in database...")
        for pred in predictions:
            await db.execute(text("""
                INSERT INTO predictions (device_id, prediction_type, confidence, severity, details)
                VALUES (:device_id, :type, :confidence, :severity, :details)
            """), {
                "device_id": test_payload.deviceId,
                "type": pred["type"],
                "confidence": pred["confidence"],
                "severity": pred["severity"],
                "details": json.dumps(pred["details"])
            })
        
        await db.commit()
        
        # Verify predictions were stored
        result = await db.execute(text("""
            SELECT prediction_type, confidence, severity, details 
            FROM predictions 
            WHERE device_id = :device_id 
            ORDER BY ts DESC LIMIT 20
        """), {"device_id": test_payload.deviceId})
        
        stored_predictions = list(result.mappings())
        
        # Count different prediction types
        ml_predictions = [p for p in stored_predictions if not p['prediction_type'].endswith('_basic')]
        ai_comments = [p for p in stored_predictions if p['prediction_type'] == 'ai_comment']
        
        print(f"\n✅ Verified {len(stored_predictions)} predictions stored in database")
        print(f"   🤖 ML Predictions: {len(ml_predictions)}")
        print(f"   💭 AI Comments: {len(ai_comments)}")
        
        if len(ml_predictions) > 0:
            print(f"\n🎯 SUCCESS: ML models are working!")
            print(f"   The system detected anomalies and made predictions based on:")
            print(f"   - Historical data patterns")
            print(f"   - Statistical analysis")
            print(f"   - Time series forecasting")
            print(f"   - Anomaly detection algorithms")
        else:
            print(f"\n⚠️  ML models didn't generate predictions. This could be due to:")
            print(f"   - Insufficient historical data")
            print(f"   - Data quality issues")
            print(f"   - Model thresholds not met")
        
        print(f"\n🌐 Check the frontend AI page to see the results!")
        print(f"💡 Gemini AI provides expert commentary on ML predictions (not making predictions)")
        
        break

if __name__ == "__main__":
    asyncio.run(test_ml_comprehensive())
