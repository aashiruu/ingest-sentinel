import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_baseline_ingestion_and_aggregates():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = datetime.now(timezone.utc)

        # Send Event 1: reading = 10.0
        resp1 = await ac.post("/api/v1/events", json={
            "event_id": "evt-001",
            "device_id": "sensor-100",
            "timestamp": t0.isoformat(),
            "reading": 10.0
        })
        assert resp1.status_code == 202

        # Send Event 2: reading = 20.0
        resp2 = await ac.post("/api/v1/events", json={
            "event_id": "evt-002",
            "device_id": "sensor-100",
            "timestamp": (t0 + timedelta(seconds=1)).isoformat(),
            "reading": 20.0
        })
        assert resp2.status_code == 202

        # Query state
        get_resp = await ac.get("/api/v1/devices/sensor-100")
        assert get_resp.status_code == 200
        data = get_resp.json()

        assert data["count"] == 2
        assert data["sum_readings"] == 30.0
        assert data["avg_reading"] == 15.0
        assert data["min_reading"] == 10.0
        assert data["max_reading"] == 20.0
        assert data["latest_reading"] == 20.0
