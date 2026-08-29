import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_out_of_order_event_handling():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t0 = datetime.now(timezone.utc)
        t_newer = t0 + timedelta(seconds=30)
        t_older = t0 + timedelta(seconds=10)

        # 1. Ingest newer event first (Reading: 100.0 at t+30s)
        resp1 = await ac.post("/api/v1/events", json={
            "event_id": "evt-newer",
            "device_id": "sensor-ooo",
            "timestamp": t_newer.isoformat(),
            "reading": 100.0
        })
        assert resp1.status_code == 202
        body1 = resp1.json()
        assert body1["is_out_of_order"] is False
        assert body1["current_aggregate"]["latest_reading"] == 100.0

        # 2. Ingest older event second (Reading: 50.0 at t+10s)
        resp2 = await ac.post("/api/v1/events", json={
            "event_id": "evt-older",
            "device_id": "sensor-ooo",
            "timestamp": t_older.isoformat(),
            "reading": 50.0
        })
        assert resp2.status_code == 202
        body2 = resp2.json()
        assert body2["is_out_of_order"] is True

        # 3. Verify State:
        # - latest_reading MUST remain 100.0 (from t+30s), NOT overwritten by 50.0
        # - Aggregate calculations must include both readings: count=2, sum=150, avg=75.0
        state_resp = await ac.get("/api/v1/devices/sensor-ooo")
        assert state_resp.status_code == 200
        state = state_resp.json()

        assert state["latest_reading"] == 100.0
        assert state["latest_timestamp"] == t_newer.isoformat()
        assert state["count"] == 2
        assert state["sum_readings"] == 150.0
        assert state["avg_reading"] == 75.0
        assert state["out_of_order_count"] == 1

        # 4. Verify historical event log is chronologically sorted
        history_resp = await ac.get("/api/v1/devices/sensor-ooo/events")
        history = history_resp.json()
        assert len(history) == 2
        assert history[0]["event_id"] == "evt-older"
        assert history[1]["event_id"] == "evt-newer"
