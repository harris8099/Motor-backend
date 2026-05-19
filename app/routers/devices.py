from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings
from app.routers.auth import require_admin_user, User
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

class DeviceCreate(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    location: Optional[str] = None
    firmware_version: Optional[str] = None

class DeviceResponse(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_seen_at: Optional[datetime]
    location: Optional[str]
    firmware_version: Optional[str]

@router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get all registered devices. Set include_inactive=true to show offline devices."""
    if include_inactive:
        # Return all devices
        result = await db.execute(text("""
            SELECT id, name, description, is_active, created_at, updated_at, 
                   last_seen_at, location, firmware_version
            FROM devices
            ORDER BY created_at DESC
        """))
    else:
        # Return only active devices (for backwards compatibility)
        result = await db.execute(text("""
            SELECT id, name, description, is_active, created_at, updated_at, 
                   last_seen_at, location, firmware_version
            FROM devices
            WHERE is_active = TRUE
            ORDER BY created_at DESC
        """))
    devices = result.mappings().all()
    return [dict(d) for d in devices]

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Get a specific device by ID"""
    result = await db.execute(text("""
        SELECT id, name, description, is_active, created_at, updated_at,
               last_seen_at, location, firmware_version
        FROM devices 
        WHERE id = :device_id
    """), {"device_id": device_id})
    device = result.mappings().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return dict(device)

@router.post("/devices", response_model=DeviceResponse)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Register a new device (idempotent: reactivates if it already exists)"""
    # Check if device already exists (may have been auto-registered by ESP32 or soft-deleted)
    existing = await db.execute(text("""
        SELECT id FROM devices WHERE id = :id
    """), {"id": device.id})

    if existing.mappings().first():
        # Device already in DB — reactivate it and update name/location if provided
        await db.execute(text("""
            UPDATE devices SET
                name        = COALESCE(:name, name),
                description = COALESCE(:description, description),
                location    = COALESCE(:location, location),
                is_active   = TRUE,
                updated_at  = NOW()
            WHERE id = :id
        """), {
            "id": device.id,
            "name": device.name or None,
            "description": device.description,
            "location": device.location,
        })
    else:
        # Brand-new device — insert it
        await db.execute(text("""
            INSERT INTO devices (id, name, description, location, created_at, updated_at)
            VALUES (:id, :name, :description, :location, NOW(), NOW())
        """), {
            "id": device.id,
            "name": device.name or device.id,
            "description": device.description,
            "location": device.location
        })

    await db.commit()

    # Return the device (created or reactivated)
    result = await db.execute(text("""
        SELECT id, name, description, is_active, created_at, updated_at,
               last_seen_at, location, firmware_version
        FROM devices
        WHERE id = :id
    """), {"id": device.id})
    return dict(result.mappings().first())

@router.post("/devices/bulk", response_model=List[DeviceResponse])
async def create_devices_bulk(
    devices: List[DeviceCreate],
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Register multiple devices at once, reactivating existing ones."""
    saved_devices = []
    
    for device in devices:
        existing = await db.execute(text("""
            SELECT id FROM devices WHERE id = :id
        """), {"id": device.id})

        if existing.mappings().first():
            await db.execute(text("""
                UPDATE devices SET
                    name        = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    location    = COALESCE(:location, location),
                    is_active   = TRUE,
                    updated_at  = NOW()
                WHERE id = :id
            """), {
                "id": device.id,
                "name": device.name or None,
                "description": device.description,
                "location": device.location,
            })
        else:
            await db.execute(text("""
                INSERT INTO devices (id, name, description, location, created_at, updated_at)
                VALUES (:id, :name, :description, :location, NOW(), NOW())
            """), {
                "id": device.id,
                "name": device.name or device.id,
                "description": device.description,
                "location": device.location
            })
        
        result = await db.execute(text("""
            SELECT id, name, description, is_active, created_at, updated_at,
                   last_seen_at, location, firmware_version
            FROM devices 
            WHERE id = :id
        """), {"id": device.id})
        saved_devices.append(dict(result.mappings().first()))
    
    await db.commit()
    
    return saved_devices

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Update a device's information"""
    # Check if device exists
    existing = await db.execute(text("""
        SELECT id FROM devices WHERE id = :device_id
    """), {"device_id": device_id})
    if not existing.mappings().first():
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Build update query dynamically
    update_fields = []
    params = {"device_id": device_id}
    
    if device_update.name is not None:
        update_fields.append("name = :name")
        params["name"] = device_update.name
    if device_update.description is not None:
        update_fields.append("description = :description")
        params["description"] = device_update.description
    if device_update.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = device_update.is_active
    if device_update.location is not None:
        update_fields.append("location = :location")
        params["location"] = device_update.location
    if device_update.firmware_version is not None:
        update_fields.append("firmware_version = :firmware_version")
        params["firmware_version"] = device_update.firmware_version
    
    if update_fields:
        update_fields.append("updated_at = NOW()")
        query = f"UPDATE devices SET {', '.join(update_fields)} WHERE id = :device_id"
        await db.execute(text(query), params)
        await db.commit()
    
    # Return updated device
    result = await db.execute(text("""
        SELECT id, name, description, is_active, created_at, updated_at,
               last_seen_at, location, firmware_version
        FROM devices 
        WHERE id = :device_id
    """), {"device_id": device_id})
    return dict(result.mappings().first())

@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
    __: User = Depends(require_admin_user),
):
    """Hard delete a device and all its related data from the database."""
    # Check device exists first
    existing = await db.execute(text("""
        SELECT id FROM devices WHERE id = :device_id
    """), {"device_id": device_id})
    if not existing.mappings().first():
        raise HTTPException(status_code=404, detail="Device not found")

    # Delete all related data (order matters due to FK constraints)
    await db.execute(text("DELETE FROM predictions WHERE device_id = :device_id"), {"device_id": device_id})
    await db.execute(text("DELETE FROM fault_events WHERE device_id = :device_id"), {"device_id": device_id})
    await db.execute(text("DELETE FROM sensor_readings WHERE device_id = :device_id"), {"device_id": device_id})
    await db.execute(text("DELETE FROM devices WHERE id = :device_id"), {"device_id": device_id})

    await db.commit()
    return {"message": "Device and all related data deleted successfully"}

@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Update device last_seen timestamp (called when device sends data)"""
    await db.execute(text("""
        INSERT INTO devices (id, last_seen_at, updated_at)
        VALUES (:device_id, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            last_seen_at = NOW(),
            updated_at = NOW()
    """), {"device_id": device_id})
    await db.commit()
    return {"message": "Heartbeat recorded"}
