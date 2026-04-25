import asyncio
import json
from app.database import get_db
from sqlalchemy import text
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.services.enhanced_prediction import run_enhanced_predictions

async def test_enhanced_predictions():
    """Test the enhanced AI prediction system"""
    async for db in get_db():
        print("🧪 Testing Enhanced AI Prediction System...")
        
        # Create test sensor payload
        test_payload = SensorPayload(
            deviceId="esp32-001",
            motor=MotorData(
                running=True,
                rpm=1450,
                pulse=24,
                uptime=3600
            ),
            uptime=3600,
            power=PowerData(
                voltage=230.5,
                current=12.8,
                power=2950.4,
                powerFactor=0.89,
                energy=2.95,
                frequency=50.1
            ),
            temperature=TemperatureData(
                t1=78.5,
                t2=76.2
            ),
            vibration=VibrationData(
                x=1.2,
                y=0.8,
                z=9.5,
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
        
        # Run enhanced predictions
        predictions = await run_enhanced_predictions(test_payload, db)
        
        print(f"\n📊 Generated {len(predictions)} enhanced predictions:")
        for i, pred in enumerate(predictions, 1):
            print(f"\n{i}. {pred['type'].upper()}")
            print(f"   Confidence: {pred['confidence']:.2f}")
            print(f"   Severity: {pred['severity']}")
            print(f"   Details: {json.dumps(pred['details'], indent=6)}")
        
        # Store predictions in database for testing
        print(f"\n💾 Storing predictions in database...")
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
            ORDER BY ts DESC LIMIT 10
        """), {"device_id": test_payload.deviceId})
        
        stored_predictions = list(result.mappings())
        print(f"\n✅ Verified {len(stored_predictions)} predictions stored in database")
        
        print("\n🎯 Enhanced AI Prediction System Test Complete!")
        print("🌐 Check the frontend AI page to see the enhanced predictions")
        
        break

if __name__ == "__main__":
    asyncio.run(test_enhanced_predictions())
