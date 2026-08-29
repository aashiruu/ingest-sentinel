import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
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

class IngestResult(BaseModel):
    status: str
    is_duplicate: bool
    device_id: str
    aggregate: DeviceAggregate

class TelemetryStore:
    def __init__(self, dedupe_ttl_seconds: int = 3600):
        self._lock = asyncio.Lock()
        self._events: Dict[str, List[StoredEvent]] = {}  # device_id -> events
        self._aggregates: Dict[str, DeviceAggregate] = {}  # device_id -> aggregate state
        self._seen_events: Dict[str, datetime] = {}  # event_id -> received_at
        self._dedupe_ttl = timedelta(seconds=dedupe_ttl_seconds)
        self.duplicate_count: int = 0

    def _purge_expired_dedupe_keys(self, now: datetime):
        cutoff = now - self._dedupe_ttl
        expired = [eid for eid, seen_at in self._seen_events.items() if seen_at < cutoff]
        for eid in expired:
            del self._seen_events[eid]

    async def record_event(self, event_id: str, device_id: str, timestamp: datetime, reading: float) -> IngestResult:
        async with self._lock:
            now = datetime.now(timezone.utc)
            self._purge_expired_dedupe_keys(now)

            if device_id not in self._aggregates:
                self._aggregates[device_id] = DeviceAggregate(device_id=device_id)
                self._events[device_id] = []

            agg = self._aggregates[device_id]

            # Deduplication Check
            if event_id in self._seen_events:
                self.duplicate_count += 1
                return IngestResult(
                    status="duplicate_ignored",
                    is_duplicate=True,
                    device_id=device_id,
                    aggregate=agg
                )

            # Mark event as seen
            self._seen_events[event_id] = now

            stored = StoredEvent(
                event_id=event_id,
                device_id=device_id,
                timestamp=timestamp,
                reading=reading,
                received_at=now
            )
            self._events[device_id].append(stored)

            # Update running stats
            agg.count += 1
            agg.sum_readings += reading
            agg.avg_reading = round(agg.sum_readings / agg.count, 2)
            agg.min_reading = reading if agg.min_reading is None else min(agg.min_reading, reading)
            agg.max_reading = reading if agg.max_reading is None else max(agg.max_reading, reading)

            if agg.latest_timestamp is None or timestamp >= agg.latest_timestamp:
                agg.latest_timestamp = timestamp
                agg.latest_reading = reading

            return IngestResult(
                status="accepted",
                is_duplicate=False,
                device_id=device_id,
                aggregate=agg
            )

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
            self._seen_events.clear()
            self.duplicate_count = 0

store = TelemetryStore()
