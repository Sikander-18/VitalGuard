"""
VitalGuard v2 — Unified FastAPI Application
Real-time healthcare monitoring with:
  - Bidirectional WebSocket (vitals, risk, decision, trend, trace)
  - REST API (users, vitals, alerts, agents, simulate)
  - Rule Engine + 5-Agent LangGraph pipeline
  - Async SQLite with SQLAlchemy
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .db.database import engine, Base
from .routes import users, doctors, vitals, alerts, agent_logs
from .services.websocket import manager
from .services.location import get_location_context
from .services.location import get_alert_safe_coordinates
from .engine.rule_engine import compute_risk
from .agents.graph import agent_graph

import asyncio
import json
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("vitalguard")

app = FastAPI(title="VitalGuard API", version="2.0.0")

# CORS for frontend dev servers
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


# ── Startup ───────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("VitalGuard v2 started — database tables ready")


# ── REST Routes ───────────────────────────────────────────────────

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
app.include_router(vitals.router, prefix="/vitals", tags=["Vitals"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(agent_logs.router, prefix="/agent-logs", tags=["Agent Logs"])

from . import simulate
app.include_router(simulate.router, prefix="/simulate", tags=["Simulate"])


# ── System Endpoints ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "VitalGuard v2 API", "version": "2.0.0", "status": "running"}


@app.get("/system/status")
async def system_status():
    """Health check with system state."""
    from .services.emergency import get_incident_status
    from .agents.llm import get_llm
    return {
        "status": "healthy",
        "version": "2.0.0",
        "llm_available": get_llm() is not None,
        "connected_ws_users": manager.connected_users,
        "incident_locks": get_incident_status(),
    }


@app.get("/hospitals/nearby")
async def get_nearby_hospitals(lat: float = 17.385, lng: float = 78.487, limit: int = 5):
    """Get nearest hospitals to a given location."""
    from .services.location import get_nearest_hospitals, HOSPITALS
    if lat is not None and lng is not None:
        return get_nearest_hospitals(lat, lng, limit=limit)
    return HOSPITALS[:limit]


# ── WebSocket — Real-Time Monitoring ──────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Bidirectional WebSocket for real-time patient monitoring.
    NO auto-simulation — data only comes from BLE relay polling
    or manual simulate triggers via REST API / dashboard buttons.

    Server → Client messages:
      {type: "vitals", data: {...}}
      {type: "risk", data: {...}}
      {type: "decision", data: {...}}
      {type: "action", data: {...}}
      {type: "trend", data: {...}}
      {type: "trace", data: {...}}
      {type: "system", data: {message: "..."}}

    Client → Server commands:
      {type: "location_update", location: {lat, lng}}
    """
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)

                if msg.get("type") == "location_update":
                    loc = msg.get("location", {})
                    logger.info(f"Location update for {user_id}: {loc}")
                    from .db.database import AsyncSessionLocal
                    from sqlalchemy.future import select
                    from .db.models import User
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(select(User).where(User.id == user_id))
                        db_user = result.scalars().first()
                        coords = get_alert_safe_coordinates(loc.get("lat"), loc.get("lng"))
                        if db_user and coords:
                            db_user.location_lat, db_user.location_lng = coords
                            await session.commit()
            except json.JSONDecodeError:
                pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(websocket, user_id)
