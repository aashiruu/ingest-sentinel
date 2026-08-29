import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_late_arrival_window_policy():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        now = datetime.now(timezone.utc)

        # 1. Event inside window (2 minutes old < 5 minutes threshold): Accepted
        inside_ts = now - timedelta(minutes=2)
        resp1 = await ac.post("/api/v1/events", json={
            "event_id": "evt-inside-window",
            "device_id": "sensor-late-test",
            "timestamp": inside_ts.isoformat(),
            "reading": 25.0
        })
        assert resp1.status_code == 202
        body1 = resp1.json()
        assert body1["status"] == "accepted"
        assert body1["is_late_rejected"] is False
        assert body1["current_aggregate"]["count"] == 1

        # 2. Event outside window (10 minutes old > 5 minutes threshold): Rejected
        outside_ts = now - timedelta(minutes=10)
        resp2 = await ac.post("/api/v1/events", json={
            "event_id": "evt-outside-window",
            "device_id": "sensor-late-test",
            "timestamp": outside_ts.isoformat(),
            "reading": 999.0
        })
        assert resp2.status_code == 202
        body2 = resp2.json()
        assert body2["status"] == "late_rejected"
        assert body2["is_late_rejected"] is True
        assert body2["current_aggregate"]["count"] == 1  # Count not incremented
        assert body2["current_aggregate"]["late_rejected_count"] == 1

        # 3. Confirm Device Aggregate unaffected by the rejected late event
        state_resp = await ac.get("/api/v1/devices/sensor-late-test")
        assert state_resp.status_code == 200
        state = state_resp.json()
        assert state["count"] == 1
        assert state["sum_readings"] == 25.0
        assert state["avg_reading"] == 25.0
        assert state["late_rejected_count"] == 1

        # 4. Verify history excludes the rejected late event
        history_resp = await ac.get("/api/v1/devices/sensor-late-test/events")
        history = history_resp.json()
        assert len(history) == 1
        assert history[0]["event_id"] == "evt-inside-window"
