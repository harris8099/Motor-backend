import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import settings
import sqlalchemy

async def main():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(sqlalchemy.text('SELECT count(*) FROM sensor_readings'))
            print("Row count:", res.scalar())
    except Exception as e:
        print("Error:", e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
