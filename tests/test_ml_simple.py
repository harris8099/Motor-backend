import asyncio
from app.services.ml_prediction import run_ml_predictions
from app.schemas import SensorPayload, MotorData, PowerData, TemperatureData, VibrationData, FaultsData, ProtectionData, MaintenanceData
from app.database import get_db

async def quick_test():
    async for db in get_db():
        # Create a problematic payload that should trigger ML predictions
        payload = SensorPayload(
            deviceId='esp32-001',
            motor=MotorData(running=True, rpm=800, pulse=24, uptime=20000),
            uptime=20000,
            power=PowerData(voltage=220.0, current=18.0, power=3960.0, powerFactor=0.85, energy=8.5, frequency=49.5),
            temperature=TemperatureData(t1=92.0, t2=90.0),
            vibration=VibrationData(x=5.2, y=4.1, z=18.8, tap=False),
            faults=FaultsData(overcurrent=False, overtemp=False, stall=False, vibration=False, overvoltage=False, undervoltage=False),
            protection=ProtectionData(maxCurrentA=15.0, maxTempC=85.0, minRpm=1200, overvoltageV=260.0, undervoltageV=200.0, stallCurrentA=18.0, startupGraceMs=5000, faultTripCount=3, vibrationAckGraceMs=10000),
            maintenance=MaintenanceData(nextMaintenanceTime='2024-12-31T23:59:59Z', totalLifeCycleHours=8500, maintenanceHoursLimit=8760, maintenanceHoursLimitSeconds=31536000, totalLifeCycleSeconds=30600000)
        )
        
        predictions = await run_ml_predictions(payload, db)
        print(f'Generated {len(predictions)} ML predictions:')
        for pred in predictions:
            print(f'  - {pred["type"]}: {pred["confidence"]:.2f} ({pred["severity"]})')
        
        if len(predictions) == 0:
            print('No ML predictions generated - checking fallback...')
            # The system should fallback to basic predictions
        break

asyncio.run(quick_test())
