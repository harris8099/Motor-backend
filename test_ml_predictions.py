import asyncio
import json
from app.database import get_db
from sqlalchemy import text
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.services.ml_prediction import run_ml_predictions

async def test_ml_predictions():
    """Test the ML-based prediction system"""
    async for db in get_db():
        print("🧪 Testing ML-Based AI Prediction System...")
        
        # Create test sensor payload with realistic values
        test_payload = SensorPayload(
            deviceId="esp32-001",
            motor=MotorData(
                running=True,
                rpm=1450,
                pulse=24,
                uptime=7200
            ),
            uptime=7200,
            power=PowerData(
                voltage=230.5,
                current=13.2,
                power=3040.6,
                powerFactor=0.89,
                energy=6.08,
                frequency=50.1
            ),
            temperature=TemperatureData(
                t1=82.5,  # Elevated temperature
                t2=80.2
            ),
            vibration=VibrationData(
                x=2.1,   # Higher vibration
                y=1.4,
                z=10.2,
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
                        if key.includes('rate') or key.includes('ratio'):
                            print(f"   {key}: {(value * 100):.1f}%")
                        elif key.includes('time'):
                            print(f"   {key}: {value:.1f}")
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
            ORDER BY ts DESC LIMIT 15
        """), {"device_id": test_payload.deviceId})
        
        stored_predictions = list(result.mappings())
        
        # Count different prediction types
        ml_predictions = [p for p in stored_predictions if not p['prediction_type'].endswith('_basic')]
        ai_comments = [p for p in stored_predictions if p['prediction_type'] == 'ai_comment']
        
        print(f"\n✅ Verified {len(stored_predictions)} predictions stored in database")
        print(f"   🤖 ML Predictions: {len(ml_predictions)}")
        print(f"   💭 AI Comments: {len(ai_comments)}")
        
        print("\n🎯 ML-Based AI Prediction System Test Complete!")
        print("🌐 Check the frontend AI page to see the ML predictions and AI commentary")
        print("📊 The ML models are now making predictions based on historical data patterns")
        print("💡 Gemini AI provides expert commentary on the ML predictions (not making predictions)")
        
        break

if __name__ == "__main__":
    asyncio.run(test_ml_predictions())
