"""
SkyGuard AI - Backend
----------------------
Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .simulator import make_default_network, Station
from .ml.engine import AnomalyEngine
from .ml.explain import explain

app = FastAPI(title="SkyGuard AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state (swap for TimescaleDB/Postgres in production - see docs/architecture.md)
# ---------------------------------------------------------------------------
STATIONS: list[Station] = make_default_network(15)
STATIONS_BY_ID: dict[str, Station] = {s.station_id: s for s in STATIONS}
ENGINE = AnomalyEngine()
for s in STATIONS:
    ENGINE.register_station(s.station_id, s.latitude, s.longitude)

RECENT_READINGS: dict[str, list[dict]] = {s.station_id: [] for s in STATIONS}
ANOMALY_FEED: list[dict] = []  # newest first, capped
MAX_FEED_LEN = 200
MAX_HISTORY_LEN = 120

CONNECTIONS: list[WebSocket] = []


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class FaultInjectionRequest(BaseModel):
    station_id: str
    fault_type: str  # SPIKE | DRIFT | FLATLINE | DROPOUT | NOISE_BURST
    parameter: str  # temperature | humidity | pressure | wind_speed | solar_radiation
    magnitude: float = 1.0
    duration_ticks: int = 40


class FeedbackRequest(BaseModel):
    anomaly_id: str
    verdict: str  # CONFIRMED | FALSE_POSITIVE
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Background simulation + detection loop
# ---------------------------------------------------------------------------
async def simulation_loop():
    while True:
        for station in STATIONS:
            reading = station.read()
            hist = RECENT_READINGS[station.station_id]
            hist.append(reading)
            if len(hist) > MAX_HISTORY_LEN:
                hist.pop(0)

            results = ENGINE.process(reading)
            broadcast_payload = {
                "type": "reading",
                "station_id": station.station_id,
                "station_name": station.name,
                "reading": reading,
                "results": [],
            }

            for r in results:
                if r.is_anomaly:
                    entry = {
                        "id": str(uuid.uuid4()),
                        "time": reading["timestamp"],
                        "station_id": station.station_id,
                        "station_name": station.name,
                        "parameter": r.parameter,
                        "raw_value": r.raw_value,
                        "corrected_value": r.corrected_value,
                        "trust_score": r.trust_score,
                        "root_cause": r.root_cause,
                        "explanation": explain(r.root_cause, r.parameter, r.raw_value, r.corrected_value, r.trust_score),
                        "model_votes": r.model_votes,
                        "status": "OPEN",
                    }
                    ANOMALY_FEED.insert(0, entry)
                    if len(ANOMALY_FEED) > MAX_FEED_LEN:
                        ANOMALY_FEED.pop()
                    broadcast_payload["results"].append(entry)

            if broadcast_payload["results"] or True:
                # always send the reading so the map/live charts update smoothly;
                # anomaly cards only render client-side when results is non-empty
                await broadcast(broadcast_payload)

        await asyncio.sleep(1.5)


async def broadcast(payload: dict):
    dead = []
    for ws in CONNECTIONS:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(simulation_loop())


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "stations": len(STATIONS), "time": time.time()}


@app.get("/api/stations")
def list_stations():
    out = []
    for s in STATIONS:
        latest = RECENT_READINGS[s.station_id][-1] if RECENT_READINGS[s.station_id] else None
        latest_trust = None
        open_anoms = [a for a in ANOMALY_FEED if a["station_id"] == s.station_id and a["status"] == "OPEN"]
        if open_anoms:
            latest_trust = min(a["trust_score"] for a in open_anoms[:5])
        else:
            latest_trust = 100.0
        out.append({
            "station_id": s.station_id,
            "name": s.name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "elevation_m": s.elevation_m,
            "latest_reading": latest,
            "trust_score": latest_trust,
            "has_active_fault": s.active_fault is not None,
        })
    return out


@app.get("/api/stations/{station_id}/readings")
def station_readings(station_id: str, limit: int = 60):
    if station_id not in RECENT_READINGS:
        return {"error": "station not found"}
    return RECENT_READINGS[station_id][-limit:]


@app.get("/api/anomalies")
def list_anomalies(status: Optional[str] = None, root_cause: Optional[str] = None, station_id: Optional[str] = None, limit: int = 50):
    feed = ANOMALY_FEED
    if status:
        feed = [a for a in feed if a["status"] == status]
    if root_cause:
        feed = [a for a in feed if a["root_cause"] == root_cause]
    if station_id:
        feed = [a for a in feed if a["station_id"] == station_id]
    return feed[:limit]


@app.post("/api/anomalies/{anomaly_id}/feedback")
def submit_feedback(anomaly_id: str, body: FeedbackRequest):
    for a in ANOMALY_FEED:
        if a["id"] == anomaly_id:
            a["status"] = "ACKNOWLEDGED" if body.verdict == "CONFIRMED" else "RESOLVED"
            a["feedback"] = {"verdict": body.verdict, "notes": body.notes}
            return {"ok": True}
    return {"ok": False, "error": "anomaly not found"}


@app.get("/api/dashboard/summary")
def dashboard_summary():
    total = len(STATIONS)
    open_anoms = [a for a in ANOMALY_FEED if a["status"] == "OPEN"]
    avg_trust = 100.0
    trusts = []
    for s in STATIONS:
        opens = [a for a in ANOMALY_FEED if a["station_id"] == s.station_id and a["status"] == "OPEN"]
        trusts.append(min([a["trust_score"] for a in opens], default=100.0))
    if trusts:
        avg_trust = round(sum(trusts) / len(trusts), 1)
    faulty = sum(1 for s in STATIONS if s.active_fault is not None)
    return {
        "total_stations": total,
        "healthy_stations": total - faulty,
        "active_alerts": len(open_anoms),
        "avg_trust_score": avg_trust,
        "root_cause_breakdown": _root_cause_breakdown(open_anoms),
    }


def _root_cause_breakdown(anoms: list[dict]) -> dict:
    out: dict[str, int] = {}
    for a in anoms:
        out[a["root_cause"]] = out.get(a["root_cause"], 0) + 1
    return out


@app.post("/api/simulate/inject-fault")
def inject_fault(body: FaultInjectionRequest):
    station = STATIONS_BY_ID.get(body.station_id)
    if not station:
        return {"ok": False, "error": "station not found"}
    station.inject_fault(body.fault_type, body.parameter, body.magnitude, body.duration_ticks)
    return {"ok": True, "message": f"Injected {body.fault_type} on {body.parameter} at {station.name}"}


@app.post("/api/simulate/reset")
def reset_simulation():
    for s in STATIONS:
        s.clear_fault()
    ANOMALY_FEED.clear()
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/live-feed")
async def ws_live_feed(websocket: WebSocket):
    await websocket.accept()
    CONNECTIONS.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive / ignore incoming
    except WebSocketDisconnect:
        if websocket in CONNECTIONS:
            CONNECTIONS.remove(websocket)
