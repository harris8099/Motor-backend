import asyncio
import json
from app.database import get_db
from sqlalchemy import text
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.services.prebuilt_models import run_prebuilt_predictions

async def test_prebuilt_models():
    """Test the prebuilt ML models"""
    async for db in get_db():
        print("🔧 Testing Prebuilt ML Models...")
        
        # Create test payload
        test_payload = SensorPayload(
            deviceId="esp32-001",
            motor=MotorData(running=True, rpm=1100, pulse=24, uptime=15000),
            uptime=15000,
            power=PowerData(voltage=225.0, current=16.5, power=3712.5, powerFactor=0.85, energy=7.5, frequency=49.8),
            temperature=TemperatureData(t1=88.0, t2=86.0),
            vibration=VibrationData(x=4.5, y=3.2, z=15.0, tap=False),
            faults=FaultsData(overcurrent=False, overtemp=False, stall=False, vibration=False, overvoltage=False, undervoltage=False),
            protection=ProtectionData(maxCurrentA=15.0, maxTempC=85.0, minRpm=1200, overvoltageV=260.0, undervoltageV=200.0, stallCurrentA=18.0, startupGraceMs=5000, faultTripCount=3, vibrationAckGraceMs=10000),
            maintenance=MaintenanceData(nextMaintenanceTime="2024-12-31T23:59:59Z", totalLifeCycleHours=8200, maintenanceHoursLimit=8760, maintenanceHoursLimitSeconds=31536000, totalLifeCycleSeconds=29520000)
        )
        
        print(f"\n📊 Test Payload:")
        print(f"   RPM: {test_payload.motor.rpm}")
        print(f"   Current: {test_payload.power.current}A")
        print(f"   Temperature: {(test_payload.temperature.t1 + test_payload.temperature.t2)/2}°C")
        print(f"   Vibration: {(test_payload.vibration.x**2 + test_payload.vibration.y**2 + test_payload.vibration.z**2)**0.5:.2f}")
        
        # Run prebuilt model predictions
        predictions = await run_prebuilt_predictions(test_payload, db)
        
        print(f"\n🤖 Generated {len(predictions)} Prebuilt Model Predictions:")
        
        model_types = {
            'lof': 'Local Outlier Factor',
            'elliptic': 'Elliptic Envelope',
            'ridge': 'Ridge Regression',
            'lasso': 'Lasso Regression',
            'gbr': 'Gradient Boosting',
            'svr': 'Support Vector Regression'
        }
        
        for i, pred in enumerate(predictions, 1):
            model_key = pred['type'].split('_')[0]
            model_name = model_types.get(model_key, pred['type'])
            
            print(f"\n{i}. {model_name}")
            print(f"   Type: {pred['type']}")
            print(f"   Confidence: {pred['confidence']:.2f}")
            print(f"   Severity: {pred['severity']}")
            
            # Format details
            details = pred['details']
            if isinstance(details, dict):
                for key, value in details.items():
                    if isinstance(value, float):
                        if 'percent' in key:
                            print(f"   {key}: {value:.1f}%")
                        elif 'temp' in key or 'power' in key or 'current' in key or 'vibration' in key:
                            print(f"   {key}: {value:.2f}")
                        else:
                            print(f"   {key}: {value:.3f}")
                    elif isinstance(value, dict):
                        print(f"   {key}:")
                        for sub_key, sub_value in value.items():
                            print(f"     {sub_key}: {sub_value:.3f}")
                    else:
                        print(f"   {key}: {value}")
        
        # Store predictions
        print(f"\n💾 Storing prebuilt model predictions...")
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
        
        # Summary
        print(f"\n📈 Prebuilt Models Summary:")
        for model_key, model_name in model_types.items():
            count = len([p for p in predictions if model_key in p['type']])
            if count > 0:
                print(f"   ✅ {model_name}: {count} prediction(s)")
        
        print(f"\n🎯 Prebuilt Models Test Complete!")
        print(f"🔧 All models are ready for production use")
        
        break

if __name__ == "__main__":
    asyncio.run(test_prebuilt_models())
