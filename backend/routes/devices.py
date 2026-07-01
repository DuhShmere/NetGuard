from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.database import get_db
from backend.models.device import Device

router = APIRouter()

@router.get("/")
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()

@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.post("/")
def create_device(payload: dict, db: Session = Depends(get_db)):
    try:
        device = Device(**payload)
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Device with hostname '{payload.get('hostname')}' already exists"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{device_id}")
def update_device(device_id: int, payload: dict, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        for key, value in payload.items():
            setattr(device, key, value)
        db.commit()
        db.refresh(device)
        return device
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Device with hostname '{payload.get('hostname')}' already exists"
        )

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"deleted": device_id}