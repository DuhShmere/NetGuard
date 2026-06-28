from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from backend.routes import devices, snapshots, compliance, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NetGuard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(devices.router,    prefix="/devices",    tags=["devices"])
app.include_router(snapshots.router,  prefix="/snapshots",  tags=["snapshots"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"])

@app.get("/health")
def health():
    return {"status": "ok"}
