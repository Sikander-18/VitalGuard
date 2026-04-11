from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .db.database import engine, Base
from .routes import users, doctors, vitals, alerts
from .services.websocket import manager

import logging

app = FastAPI(title="PulseGuard API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Create all tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)

# Include routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
app.include_router(vitals.router, prefix="/vitals", tags=["Vitals"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

from . import simulate
app.include_router(simulate.router, prefix="/simulate", tags=["Simulate"])

# Add websocket directly in main or a separate route. Here in main for simplicity:
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't really expect clients to send messages, just listen.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.get("/")
def root():
    return {"message": "Welcome to PulseGuard API"}
