"""
VitalGuard — FastAPI Application v2
Multi-patient WebSocket streaming with:
  - Per-patient simulator + history
  - Patient profile switching API
  - Trend data passed to risk engine and agents
  - Agent trace endpoint for explainability panel
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from simulator import WearableSimulator, PATIENT_PROFILES
from risk_engine import compute_risk
from agents import run_agent
from actions import get_twilio_status

app = FastAPI(title="VitalGuard", version="2.0.0")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/twilio-status")
async def twilio_status():
    return JSONResponse(get_twilio_status())


@app.get("/api/patients")
async def patient_profiles():
    """Return available patient profiles for the UI selector."""
    return JSONResponse({
        k: {"label": v["label"]}
        for k, v in PATIENT_PROFILES.items()
    })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Multi-patient WebSocket endpoint.
    Accepts: set_mode, location_update, set_profile commands.
    Emits: vitals, risk, decision, action, trend, system, error messages.
    """
    await ws.accept()

    simulator = WearableSimulator(patient_profile="healthy_adult", patient_id="P001")
    running   = True
    current_location = {"lat": None, "lng": None}

    async def listen_for_commands():
        nonlocal running, current_location
        try:
            while running:
                data = await ws.receive_text()
                try:
                    msg = json.loads(data)

                    if msg.get("type") == "set_mode":
                        mode = msg.get("mode", "normal")
                        if mode in ("normal", "mild_anomaly", "critical_emergency", "auto"):
                            simulator.set_mode(mode)
                            await ws.send_json({
                                "type": "system",
                                "message": f"Mode → {mode.replace('_', ' ').title()}",
                            })

                    elif msg.get("type") == "location_update":
                        current_location = msg.get("location", {"lat": None, "lng": None})

                    elif msg.get("type") == "set_profile":
                        profile = msg.get("profile", "healthy_adult")
                        simulator.set_profile(profile)
                        label = PATIENT_PROFILES.get(profile, {}).get("label", profile)
                        await ws.send_json({
                            "type": "system",
                            "message": f"Patient profile → {label}",
                        })

                except json.JSONDecodeError:
                    pass
        except (WebSocketDisconnect, Exception):
            running = False

    async def monitoring_loop():
        nonlocal running
        try:
            while running:
                vitals_obj = simulator.generate()
                vitals     = vitals_obj.to_dict()
                await ws.send_json({"type": "vitals", "data": vitals})

                # Pass history to risk engine for trend analysis
                risk_assessment = await compute_risk(vitals_obj, simulator.history)
                risk = risk_assessment.to_dict()
                await ws.send_json({"type": "risk", "data": risk})

                # Send trend separately so UI can display predictive panel
                if risk.get("trend_summary"):
                    await ws.send_json({
                        "type": "trend",
                        "data": {
                            "summary": risk["trend_summary"],
                            "alert": risk.get("trend_alert"),
                            "mews": risk.get("mews_score"),
                        },
                    })

                try:
                    agent_result = await asyncio.wait_for(
                        run_agent(vitals, risk, current_location),
                        timeout=25.0,
                    )
                    await ws.send_json({"type": "decision", "data": agent_result})

                    if "action_result" in agent_result:
                        await ws.send_json({
                            "type": "action",
                            "data": agent_result["action_result"],
                        })

                    # Send explainability trace
                    if agent_result.get("explainability_trace"):
                        await ws.send_json({
                            "type": "trace",
                            "data": agent_result["explainability_trace"],
                        })

                except asyncio.TimeoutError:
                    await ws.send_json({
                        "type": "decision",
                        "data": {
                            "vitals": vitals,
                            "risk_score": risk["score"],
                            "risk_level": risk["level"],
                            "mews_score": risk.get("mews_score"),
                            "trend_alert": risk.get("trend_alert"),
                            "clinical_analysis": "[Agent timeout] Vitals recorded.",
                            "decided_action": "log" if risk["score"] <= 60 else "alert_user",
                            "action_reasoning": "Agent timeout — deterministic fallback.",
                            "trigger_vitals": risk.get("contributing_factors", []),
                            "action_result": {"action_type": "log", "success": True, "message": "Logged (timeout fallback)"},
                            "explainability_trace": [{"step": "timeout", "output": "Agent exceeded 25s"}],
                        },
                    })
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Agent error: {str(e)}"})

                await asyncio.sleep(1)

        except (WebSocketDisconnect, Exception):
            running = False

    listener = asyncio.create_task(listen_for_commands())
    monitor  = asyncio.create_task(monitoring_loop())

    try:
        await asyncio.gather(listener, monitor, return_exceptions=True)
    finally:
        running = False
        listener.cancel()
        monitor.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
