import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_metrics_endpoint_and_counters():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        now = datetime.now(timezone.utc)
        dev = "sensor-obs-001"

        # 1. Normal Event
        await ac.post("/api/v1/events", json={
            "event_id": "obs-evt-1",
            "device_id": dev,
            "timestamp": now.isoformat(),
            "reading": 15.0
        })

        # 2. Duplicate Event
        await ac.post("/api/v1/events", json={
            "event_id": "obs-evt-1",
            "device_id": dev,
            "timestamp": now.isoformat(),
            "reading": 15.0
        })

        # 3. Out-of-order Event
        await ac.post("/api/v1/events", json={
            "event_id": "obs-evt-2",
            "device_id": dev,
            "timestamp": (now - timedelta(seconds=10)).isoformat(),
            "reading": 12.0
        })

        # 4. Late Rejected Event
        await ac.post("/api/v1/events", json={
            "event_id": "obs-evt-3",
            "device_id": dev,
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "reading": 99.0
        })

        # Check /metrics endpoint
        metrics_resp = await ac.get("/metrics")
        assert metrics_resp.status_code == 200
        content = metrics_resp.text

        # Verify expected Prometheus metric labels exist
        assert 'telemetry_events_ingested_total{status="accepted"}' in content
        assert 'telemetry_events_ingested_total{status="duplicate_ignored"}' in content
        assert 'telemetry_events_ingested_total{status="late_rejected"}' in content
        assert 'telemetry_events_disorder_total{type="out_of_order"}' in content
        assert 'telemetry_events_disorder_total{type="late_arrival"}' in content
        assert 'telemetry_events_disorder_total{type="duplicate"}' in content
        assert 'telemetry_active_devices_total' in content
