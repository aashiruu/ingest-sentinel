import argparse
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta
import httpx

async def send_event(client: httpx.AsyncClient, base_url: str, event: dict):
    try:
        response = await client.post(f"{base_url}/api/v1/events", json=event)
        print(f"[{response.status_code}] Sent: {event['event_id'][:8]}.. | Device: {event['device_id']} | Val: {event['reading']:.2f} | TS: {event['timestamp']}")
    except Exception as exc:
        print(f"Failed to send event {event['event_id']}: {exc}")

async def run_simulation(base_url: str, count: int, mode: str):
    devices = [f"sensor-{i:03d}" for i in range(1, 4)]
    now = datetime.now(timezone.utc)

    # 1. Generate base sequential events
    events = []
    for i in range(count):
        dev = random.choice(devices)
        event_time = now + timedelta(seconds=i * 2)
        events.append({
            "event_id": str(uuid.uuid4()),
            "device_id": dev,
            "timestamp": event_time.isoformat(),
            "reading": round(20.0 + random.uniform(-2.0, 5.0), 2)
        })

    # 2. Inject behavior based on mode
    if mode == "normal":
        pass
    elif mode == "duplicates":
        if events:
            # Pick an existing event and append it again
            dup = events[0].copy()
            events.append(dup)
    elif mode == "out-of-order":
        random.shuffle(events)
    elif mode == "delayed":
        if events:
            # Artificially push timestamps backward
            events[-1]["timestamp"] = (now - timedelta(minutes=15)).isoformat()
    elif mode == "disorder":
        # Chaos mode: shuffle, add duplicates, skew timestamps
        if len(events) >= 2:
            events.append(events[0].copy())
            events[1]["timestamp"] = (now - timedelta(minutes=10)).isoformat()
        random.shuffle(events)

    async with httpx.AsyncClient() as client:
        for ev in events:
            await send_event(client, base_url, ev)
            await asyncio.sleep(0.05)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate IoT fleet telemetry")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Ingestion base URL")
    parser.add_argument("--count", type=int, default=5, help="Number of baseline events")
    parser.add_argument("--mode", choices=["normal", "duplicates", "out-of-order", "delayed", "disorder"], default="normal")
    args = parser.parse_args()

    asyncio.run(run_simulation(args.url, args.count, args.mode))
