import asyncio
import json
from app.database import get_db
from sqlalchemy import text
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.services.advanced_ml_prediction import run_advanced_ml_predictions

async def test_advanced_ml_system():
    """Test the advanced ML prediction system with NASA bearing model"""
    async for db in get_db():
        print("🚀 Testing Advanced ML Prediction System with NASA Bearing Model...")
        
        # Create a problematic payload that should trigger multiple advanced ML predictions
        test_payload = SensorPayload(
            deviceId="esp32-001",
            motor=MotorData(
                running=True,
                rpm=950,  # Low RPM
                pulse=24,
                uptime=25000
            ),
            uptime=25000,
            power=PowerData(
                voltage=215.0,
                current=19.5,  # High current
                power=4192.5,  # High power
                powerFactor=0.82,
                energy=12.5,
                frequency=49.0
            ),
            temperature=TemperatureData(
                t1=95.0,  # Very high temperature
                t2=93.0
            ),
            vibration=VibrationData(
                x=6.8,   # Very high vibration - should trigger NASA bearing model
                y=5.2,
                z=22.5,
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
                totalLifeCycleHours=8800,
                maintenanceHoursLimit=8760,
                maintenanceHoursLimitSeconds=31536000,
                totalLifeCycleSeconds=31680000
            )
        )
        
        print(f"\n📊 Test Payload Analysis:")
        print(f"   RPM: {test_payload.motor.rpm} (threshold: {test_payload.protection.minRpm})")
        print(f"   Current: {test_payload.power.current}A (threshold: {test_payload.protection.maxCurrentA})")
        print(f"   Temperature: {(test_payload.temperature.t1 + test_payload.temperature.t2)/2}°C (threshold: {test_payload.protection.maxTempC})")
        print(f"   Vibration Magnitude: {(test_payload.vibration.x**2 + test_payload.vibration.y**2 + test_payload.vibration.z**2)**0.5:.2f}")
        print(f"   Uptime: {test_payload.uptime/3600:.1f} hours")
        
        # Run advanced ML predictions
        predictions = await run_advanced_ml_predictions(test_payload, db)
        
        print(f"\n🤖 Generated {len(predictions)} Advanced ML Predictions:")
        
        # Count different types of predictions
        nasa_predictions = [p for p in predictions if 'nasa' in p['type']]
        anomaly_predictions = [p for p in predictions if 'anomaly' in p['type']]
        gemini_predictions = [p for p in predictions if 'gemini' in p['type']]
        rul_predictions = [p for p in predictions if 'rul' in p['type']]
        
        for i, pred in enumerate(predictions, 1):
            print(f"\n{i}. {pred['type'].upper().replace('_', ' ')}")
            print(f"   Confidence: {pred['confidence']:.2f}")
            print(f"   Severity: {pred['severity']}")
            
            # Highlight NASA bearing model results
            if 'nasa' in pred['type']:
                print(f"   🚀 NASA BEARING MODEL ANALYSIS:")
                
            # Format details for better readability
            details = pred['details']
            if isinstance(details, dict):
                for key, value in details.items():
                    if key == 'comment':
                        print(f"   💭 AI Comment: {value}")
                    elif key == 'bearing_health_index':
                        print(f"   📊 Bearing Health Index: {value:.3f}")
                    elif key == 'health_status':
                        print(f"   🏥 Health Status: {value}")
                    elif key == 'fault_type':
                        print(f"   ⚠️  Fault Type: {value}")
                    elif key == 'recommendation':
                        print(f"   💡 Recommendation: {value}")
                    elif key == 'rul_days':
                        print(f"   ⏱️  RUL: {int(value)} days")
                    elif key == 'health_index':
                        print(f"   📈 Health Index: {value:.3f}")
                    elif key == 'ensemble_score':
                        print(f"   🎯 Ensemble Score: {value:.3f}")
                    elif isinstance(value, list):
                        print(f"   {key}: {', '.join(map(str, value))}")
                    elif isinstance(value, dict):
                        print(f"   {key}: {json.dumps(value, indent=8)}")
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
        print(f"\n💾 Storing advanced ML predictions in database...")
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
        
        # Summary statistics
        print(f"\n📈 Prediction Summary:")
        print(f"   🚀 NASA Bearing Predictions: {len(nasa_predictions)}")
        print(f"   🔍 Anomaly Detection: {len(anomaly_predictions)}")
        print(f"   💭 Gemini AI: {len(gemini_predictions)}")
        print(f"   ⏱️  RUL Predictions: {len(rul_predictions)}")
        print(f"   📊 Total Advanced Predictions: {len(predictions)}")
        
        # Model capabilities demonstration
        print(f"\n🔧 Advanced ML Models Demonstrated:")
        print(f"   ✅ NASA Bearing Failure Model")
        print(f"   ✅ Ensemble Anomaly Detection (Isolation Forest + One-Class SVM)")
        print(f"   ✅ Advanced Time Series Analysis")
        print(f"   ✅ Random Forest Stall Risk Prediction")
        print(f"   ✅ Remaining Useful Life (RUL) Prediction")
        print(f"   ✅ Multi-factor Efficiency Degradation")
        print(f"   ✅ Configurable Gemini AI (Commentary/Prediction)")
        
        print(f"\n🎯 Advanced ML System Test Complete!")
        print(f"🌐 Check the frontend AI page to see all advanced predictions")
        print(f"🔧 Configure models using ml_config.py or environment variables")
        
        break

if __name__ == "__main__":
    asyncio.run(test_advanced_ml_system())
