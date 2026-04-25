import asyncio
from app.database import get_db
from sqlalchemy import text

async def verify_data():
    async for db in get_db():
        print("🔍 VERIFYING DUMMY DATA...")
        
        # Check devices
        devices = await db.execute(text("""
            SELECT id, name, is_active, last_seen_at 
            FROM devices 
            WHERE id LIKE 'esp32-%' OR id LIKE 'motor-%' 
            ORDER BY id
        """))
        print("\n📱 DEVICES:")
        for device in devices.mappings():
            status = "🟢 Online" if device['last_seen_at'] else "🔴 Offline"
            print(f"  {device['id']} - {device['name']} - {status}")
        
        # Check predictions
        predictions = await db.execute(text("""
            SELECT device_id, prediction_type, confidence, severity, ts 
            FROM predictions 
            WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'
            ORDER BY ts DESC LIMIT 10
        """))
        print("\n🤖 RECENT PREDICTIONS:")
        for pred in predictions.mappings():
            conf_emoji = "🔴" if pred['confidence'] > 0.8 else "🟡" if pred['confidence'] > 0.5 else "🟢"
            sev_emoji = "⚠️" if pred['severity'] == 'high' else "⚡" if pred['severity'] == 'medium' else "✅"
            print(f"  {pred['device_id']} - {pred['prediction_type']} - {conf_emoji} {pred['confidence']:.2f} - {sev_emoji} {pred['severity']}")
        
        # Check sensor data
        readings = await db.execute(text("""
            SELECT device_id, COUNT(*) as count, MAX(ts) as latest
            FROM sensor_readings 
            WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'
            GROUP BY device_id
            ORDER BY device_id
        """))
        print("\n📊 SENSOR DATA:")
        for reading in readings.mappings():
            print(f"  {reading['device_id']} - {reading['count']} readings")
        
        # Check fault events
        faults = await db.execute(text("""
            SELECT device_id, fault_type, COUNT(*) as count
            FROM fault_events 
            WHERE device_id LIKE 'esp32-%' OR device_id LIKE 'motor-%'
            GROUP BY device_id, fault_type
            ORDER BY device_id, count DESC
        """))
        print("\n⚠️ FAULT EVENTS:")
        for fault in faults.mappings():
            print(f"  {fault['device_id']} - {fault['fault_type']} - {fault['count']} events")
        
        print("\n✅ Data verification complete!")
        print("🌐 You can now test the ML predictions on the website!")
        break

if __name__ == "__main__":
    asyncio.run(verify_data())
