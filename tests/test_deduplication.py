import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_duplicate_event_rejection():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = datetime.now(timezone.utc)
        payload = {
            "event_id": "duplicate-uuid-999",
            "device_id": "sensor-dedupe-test",
            "timestamp": t0.isoformat(),
            "reading": 42.0
        }

        # 1. First Ingestion: Should be accepted
        resp1 = await ac.post("/api/v1/events", json=payload)
        assert resp1.status_code == 202
        body1 = resp1.json()
        assert body1["status"] == "accepted"
        assert body1["is_duplicate"] is False
        assert body1["current_aggregate"]["count"] == 1
        assert body1["current_aggregate"]["sum_readings"] == 42.0

        # 2. Duplicate Ingestion: Should be flagged as duplicate and ignored in aggregates
        resp2 = await ac.post("/api/v1/events", json=payload)
        assert resp2.status_code == 202
        body2 = resp2.json()
        assert body2["status"] == "duplicate_ignored"
        assert body2["is_duplicate"] is True
        assert body2["current_aggregate"]["count"] == 1
        assert body2["current_aggregate"]["sum_readings"] == 42.0
        assert body2["current_aggregate"]["avg_reading"] == 42.0

        # 3. Confirm Device State via GET endpoint
        get_resp = await ac.get("/api/v1/devices/sensor-dedupe-test")
        assert get_resp.status_code == 200
        state = get_resp.json()
        assert state["count"] == 1
        assert state["sum_readings"] == 42.0
