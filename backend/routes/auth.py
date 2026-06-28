from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, jwt, datetime

router = APIRouter()
SECRET = os.getenv("JWT_SECRET", "change-me-in-production")

class LoginPayload(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(payload: LoginPayload):
    # TODO: validate against users table with bcrypt
    if payload.username == "admin" and payload.password == "netguard":
        token = jwt.encode(
            {"sub": payload.username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)},
            SECRET, algorithm="HS256"
        )
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")
