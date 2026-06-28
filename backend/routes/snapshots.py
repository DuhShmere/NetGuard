from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.snapshot import ConfigSnapshot

router = APIRouter()

@router.get("/{device_id}")
def get_snapshots(device_id: int, limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(ConfigSnapshot)
        .filter(ConfigSnapshot.device_id == device_id)
        .order_by(ConfigSnapshot.collected_at.desc())
        .limit(limit)
        .all()
    )
