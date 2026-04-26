#!/usr/bin/env python3
"""Seed script to add sample devices to the database."""
import asyncio
import sys
sys.path.insert(0, "c:\\Users\\TUF\\Desktop\\Main project\\AI ml backend")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.database import settings

# Fix database URL for asyncpg
url = settings.database_url
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
url = url.split("?")[0]

engine = create_async_engine(url, connect_args={"ssl": "require"})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sample devices to create
SAMPLE_DEVICES = [
    {
        "id": "esp32-001",
        "name": "Motor A - Assembly Line 1",
        "description": "Main conveyor motor at assembly station",
        "location": "Factory Floor - Section A",
        "is_active": True,
    },
    {
        "id": "esp32-002",
        "name": "Motor B - Assembly Line 2",
        "description": "Secondary conveyor motor",
        "location": "Factory Floor - Section B",
        "is_active": True,
    },
    {
        "id": "esp32-003",
        "name": "Pump Motor - Cooling System",
        "description": "Water circulation pump for cooling",
        "location": "Utility Room",
        "is_active": True,
    },
    {
        "id": "esp32-004",
        "name": "HVAC Fan Motor",
        "description": "Ventilation fan motor",
        "location": "Roof - HVAC Unit",
        "is_active": True,
    },
    {
        "id": "esp32-005",
        "name": "Test Motor",
        "description": "Testing and calibration unit",
        "location": "Lab",
        "is_active": True,
    },
]


async def seed_devices():
    """Add sample devices to the database."""
    async with AsyncSessionLocal() as db:
        print("Seeding devices...")
        
        for device in SAMPLE_DEVICES:
            # Check if device already exists
            result = await db.execute(
                text("SELECT id FROM devices WHERE id = :id"),
                {"id": device["id"]}
            )
            existing = result.mappings().first()
            
            if existing:
                print(f"  Device {device['id']} already exists, updating...")
                await db.execute(text("""
                    UPDATE devices SET
                        name = :name,
                        description = :description,
                        location = :location,
                        is_active = :is_active,
                        updated_at = NOW()
                    WHERE id = :id
                """), device)
            else:
                print(f"  Creating device {device['id']}...")
                await db.execute(text("""
                    INSERT INTO devices (id, name, description, location, is_active, created_at, updated_at)
                    VALUES (:id, :name, :description, :location, :is_active, NOW(), NOW())
                """), device)
        
        await db.commit()
        print("Done! Sample devices created.")
        
        # Show all devices
        result = await db.execute(text("""
            SELECT id, name, is_active, created_at 
            FROM devices 
            ORDER BY created_at DESC
        """))
        devices = result.mappings().all()
        
        print(f"\nTotal devices in database: {len(devices)}")
        for d in devices:
            status = "Active" if d.is_active else "Inactive"
            print(f"  - {d.id}: {d.name} ({status})")


if __name__ == "__main__":
    asyncio.run(seed_devices())
