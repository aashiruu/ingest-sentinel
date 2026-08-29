import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

class DeviceAggregate(BaseModel):
    device_id: str
    count: int = 0
    sum_readings: float = 0.0
    avg_reading: float = 0.0
    min_reading: Optional[float] = None
    max_reading: Optional[float] = None
    latest_reading: Optional[float] = None
    latest_timestamp: Optional[datetime] = None

class StoredEvent(BaseModel):
    event_id: str
    device_id: str
    timestamp: datetime
    reading: float
    received_at: datetime

class TelemetryStore:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._events: Dict[str, List[StoredEvent]] = {}  # device_id -> list of events
        self._aggregates: Dict[str, DeviceAggregate] = {}  # device_id -> aggregate state

    async def record_event(self, event_id: str, device_id: str, timestamp: datetime, reading: float) -> DeviceAggregate:
        async with self._lock:
            stored = StoredEvent(
                event_id=event_id,
                device_id=device_id,
                timestamp=timestamp,
                reading=reading,
                received_at=datetime.utcnow()
            )

            if device_id not in self._events:
                self._events[device_id] = []
                self._aggregates[device_id] = DeviceAggregate(device_id=device_id)

            self._events[device_id].append(stored)
            agg = self._aggregates[device_id]

            # Update running stats
            agg.count += 1
            agg.sum_readings += reading
            agg.avg_reading = round(agg.sum_readings / agg.count, 2)
            agg.min_reading = reading if agg.min_reading is None else min(agg.min_reading, reading)
            agg.max_reading = reading if agg.max_reading is None else max(agg.max_reading, reading)

            # Baseline assumption: latest timestamp received sets latest reading
            if agg.latest_timestamp is None or timestamp >= agg.latest_timestamp:
                agg.latest_timestamp = timestamp
                agg.latest_reading = reading

            return agg

    async def get_device_state(self, device_id: str) -> Optional[DeviceAggregate]:
        async with self._lock:
            return self._aggregates.get(device_id)

    async def get_all_states(self) -> Dict[str, DeviceAggregate]:
        async with self._lock:
            return {k: v.model_copy() for k, v in self._aggregates.items()}

    async def reset(self):
        async with self._lock:
            self._events.clear()
            self._aggregates.clear()

store = TelemetryStore()
