from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.compliance import ComplianceResult

router = APIRouter()

@router.get("/")
def all_compliance(db: Session = Depends(get_db)):
    return db.query(ComplianceResult).order_by(ComplianceResult.evaluated_at.desc()).all()

@router.get("/{device_id}")
def device_compliance(device_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ComplianceResult)
        .filter(ComplianceResult.device_id == device_id)
        .order_by(ComplianceResult.evaluated_at.desc())
        .first()
    )
