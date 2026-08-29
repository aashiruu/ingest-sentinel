import pytest
import random
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.storage import store

@pytest.mark.asyncio
async def test_full_disorder_simulation():
    await store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        now = datetime.now(timezone.utc)
        device_id = "sensor-chaos-001"

        # Construct Ground Truth Dataset for sensor-chaos-001:
        # Event A: t = now - 60s (valid), reading = 20.0
        # Event B: t = now - 40s (valid), reading = 30.0
        # Event C: t = now - 20s (valid, highest timestamp -> latest reading), reading = 25.0
        # Event D: t = now - 10m (late rejected -> outside 5m window), reading = 999.0
        # Duplicate C: Duplicate of Event C (should be ignored)
        # Duplicate A: Duplicate of Event A (should be ignored)

        event_a = {
            "event_id": "evt-chaos-a",
            "device_id": device_id,
            "timestamp": (now - timedelta(seconds=60)).isoformat(),
            "reading": 20.0
        }
        event_b = {
            "event_id": "evt-chaos-b",
            "device_id": device_id,
            "timestamp": (now - timedelta(seconds=40)).isoformat(),
            "reading": 30.0
        }
        event_c = {
            "event_id": "evt-chaos-c",
            "device_id": device_id,
            "timestamp": (now - timedelta(seconds=20)).isoformat(),
            "reading": 25.0
        }
        event_d_late = {
            "event_id": "evt-chaos-d-late",
            "device_id": device_id,
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "reading": 999.0
        }

        # Inject disorder:
        # Delivery Order: C (newest valid) -> A (older valid, OOO) -> D (stale) -> C (dup) -> B (OOO) -> A (dup)
        delivery_stream = [
            event_c,
            event_a,
            event_d_late,
            event_c,
            event_b,
            event_a
        ]

        responses = []
        for ev in delivery_stream:
            resp = await ac.post("/api/v1/events", json=ev)
            assert resp.status_code == 202
            responses.append(resp.json())

        # Inspect responses
        # 1. Event C: accepted, normal
        assert responses[0]["status"] == "accepted"
        assert responses[0]["is_duplicate"] is False
        assert responses[0]["is_out_of_order"] is False

        # 2. Event A: accepted, out of order (timestamp < C)
        assert responses[1]["status"] == "accepted"
        assert responses[1]["is_out_of_order"] is True

        # 3. Event D: late rejected
        assert responses[2]["status"] == "late_rejected"
        assert responses[2]["is_late_rejected"] is True

        # 4. Event C duplicate: ignored
        assert responses[3]["status"] == "duplicate_ignored"
        assert responses[3]["is_duplicate"] is True

        # 5. Event B: accepted, out of order (timestamp < C)
        assert responses[4]["status"] == "accepted"
        assert responses[4]["is_out_of_order"] is True

        # 6. Event A duplicate: ignored
        assert responses[5]["status"] == "duplicate_ignored"
        assert responses[5]["is_duplicate"] is True

        # Assert Final Stored Device State
        # Valid accepted readings: A (20.0), B (30.0), C (25.0)
        # Expected count = 3, sum = 75.0, avg = 25.0, min = 20.0, max = 30.0
        # Expected latest_reading = 25.0 (from Event C, which had latest timestamp)
        # Expected out_of_order_count = 2 (A and B arrived after C)
        # Expected late_rejected_count = 1 (Event D)
        state_resp = await ac.get(f"/api/v1/devices/{device_id}")
        assert state_resp.status_code == 200
        state = state_resp.json()

        assert state["count"] == 3
        assert state["sum_readings"] == 75.0
        assert state["avg_reading"] == 25.0
        assert state["min_reading"] == 20.0
        assert state["max_reading"] == 30.0
        assert state["latest_reading"] == 25.0
        assert state["out_of_order_count"] == 2
        assert state["late_rejected_count"] == 1

        # Verify historical event log is ordered strictly by event timestamp: A -> B -> C
        history_resp = await ac.get(f"/api/v1/devices/{device_id}/events")
        history = history_resp.json()
        assert len(history) == 3
        assert history[0]["event_id"] == "evt-chaos-a"
        assert history[1]["event_id"] == "evt-chaos-b"
        assert history[2]["event_id"] == "evt-chaos-c"
