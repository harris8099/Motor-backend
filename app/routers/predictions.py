from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, settings

router = APIRouter()

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.get("/predictions/{device_id}")
async def get_predictions(
    device_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    result = await db.execute(text("""
        SELECT * FROM predictions
        WHERE device_id = :device_id
        ORDER BY ts DESC LIMIT :limit
    """), {"device_id": device_id, "limit": limit})
    rows = result.mappings().all()
    return {"data": [dict(r) for r in rows]}
