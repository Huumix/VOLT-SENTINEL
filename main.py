"""In-memory ESP32 telemetry API for Volt Sentinel."""
import logging
import math
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("volt_sentinel")

OFFLINE_TIMEOUT = int(os.getenv("NODE_OFFLINE_TIMEOUT_SECONDS", "15"))
origins = [item.strip() for item in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if item.strip()]

app = FastAPI(title="Volt Sentinel API")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
latest_nodes: dict[str, dict] = {}


class TelemetryIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    voltage: float
    current: float
    signal_strength: Optional[float] = None
    temperature: Optional[float] = None
    frequency: Optional[float] = None
    timestamp: Optional[str] = None

    @field_validator("device_id")
    @classmethod
    def clean_device_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("device_id is required")
        return value

    @field_validator("voltage", "current", "signal_strength", "temperature", "frequency")
    @classmethod
    def finite_value(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not math.isfinite(value):
            raise ValueError("sensor values must be finite")
        return value


def node_status(node: dict) -> str:
    age = (datetime.now(timezone.utc) - node["last_seen_at"]).total_seconds()
    return "ONLINE" if age <= OFFLINE_TIMEOUT else "OFFLINE"


def public_node(node: dict) -> dict:
    return {key: value for key, value in node.items() if key != "last_seen_at"} | {"status": node_status(node)}


def ordered_nodes() -> list[dict]:
    return sorted((public_node(node) for node in latest_nodes.values()), key=lambda n: n["device_id"])


def infer_span(nodes: list[dict]) -> tuple[Optional[str], Optional[str]]:
    def index(node: dict) -> int:
        digits = "".join(char for char in node["device_id"] if char.isdigit())
        return int(digits) if digits else 10**9
    sorted_nodes = sorted(nodes, key=index)
    for previous, current in zip(sorted_nodes, sorted_nodes[1:]):
        if previous["status"] == "ONLINE" and current["status"] == "OFFLINE":
            return previous["device_id"], current["device_id"]
    return None, None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/sensors/data")
def receive_telemetry(data: TelemetryIn):
    if not 0 <= data.voltage <= 1000 or not 0 <= data.current <= 1000:
        logger.warning("Rejected out-of-range telemetry from %s", data.device_id)
        raise HTTPException(status_code=422, detail="Invalid sensor value")
    now = datetime.now(timezone.utc)
    node = data.model_dump(exclude_none=True)
    node["power"] = round(data.voltage * data.current, 2)
    node["last_seen"] = now.isoformat()
    node["last_seen_at"] = now
    latest_nodes[data.device_id] = node
    logger.info("Telemetry received from %s", data.device_id)
    return {"success": True, "device_id": data.device_id, "message": "Telemetry received"}


@app.get("/api/nodes")
def get_nodes():
    return ordered_nodes()


@app.get("/api/dashboard/summary")
def dashboard_summary():
    nodes = ordered_nodes()
    online = [node for node in nodes if node["status"] == "ONLINE"]
    affected_from, affected_to = infer_span(nodes)
    last = online[-1] if online else {}
    return {
        "system_status": "FAULT" if affected_to else ("NORMAL" if nodes else "WAITING"),
        "total_nodes": len(nodes), "online_nodes": len(online),
        "offline_nodes": len(nodes) - len(online),
        "affected_from": affected_from, "affected_to": affected_to,
        "line_voltage": last.get("voltage"), "line_current": last.get("current"),
    }
