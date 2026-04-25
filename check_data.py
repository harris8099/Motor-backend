import asyncio
from app.database import get_db
from sqlalchemy import text

async def check_data():
    async for db in get_db():
        result = await db.execute(text('SELECT COUNT(*) as count FROM sensor_readings WHERE device_id = :device_id'), {"device_id": "esp32-001"})
        count = result.scalar()
        print(f'Sensor readings for esp32-001: {count}')
        
        if count > 0:
            result = await db.execute(text('SELECT ts, power, temp1, temp2 FROM sensor_readings WHERE device_id = :device_id ORDER BY ts DESC LIMIT 5'), {"device_id": "esp32-001"})
            for row in result.mappings():
                print(f'  {row["ts"]}: Power={row["power"]}, Temp1={row["temp1"]}, Temp2={row["temp2"]}')
        
        # Check all devices
        result = await db.execute(text('SELECT device_id, COUNT(*) as count FROM sensor_readings GROUP BY device_id'))
        print('\nAll devices data count:')
        for row in result.mappings():
            print(f'  {row["device_id"]}: {row["count"]} readings')
        
        break

asyncio.run(check_data())
