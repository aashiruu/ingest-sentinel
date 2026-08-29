from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.storage import store, DeviceAggregate, StoredEvent

app = FastAPI(
    title="ingest-sentinel",
    description="Telemetry ingestion service exploring out-of-order, duplicate, and late event handling."
)

class TelemetryEvent(BaseModel):
    event_id: str = Field(..., description="Globally unique UUID for the event")
    device_id: str = Field(..., description="Identifier for the transmitting device")
    timestamp: datetime = Field(..., description="Timestamp when measurement was taken at the sensor")
    reading: float = Field(..., description="Telemetry metric value (e.g., temperature)")

@app.get("/healthz", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(event: TelemetryEvent):
    result = await store.record_event(
        event_id=event.event_id,
        device_id=event.device_id,
        timestamp=event.timestamp,
        reading=event.reading
    )
    return {
        "status": result.status,
        "is_duplicate": result.is_duplicate,
        "is_out_of_order": result.is_out_of_order,
        "is_late_rejected": result.is_late_rejected,
        "device_id": result.device_id,
        "current_aggregate": result.aggregate
    }

@app.get("/api/v1/devices/{device_id}", response_model=DeviceAggregate)
async def get_device(device_id: str):
    state = await store.get_device_state(device_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return state

@app.get("/api/v1/devices/{device_id}/events", response_model=List[StoredEvent])
async def get_device_history(device_id: str):
    return await store.get_device_events(device_id)

@app.get("/api/v1/devices")
async def list_devices():
    return await store.get_all_states()
