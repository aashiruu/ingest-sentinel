from datetime import datetime
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

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
    # Stage 0 accepts and echoes the payload structure without persistent storage
    return {
        "status": "received",
        "event_id": event.event_id,
        "device_id": event.device_id,
        "timestamp": event.timestamp.isoformat(),
        "reading": event.reading
    }
