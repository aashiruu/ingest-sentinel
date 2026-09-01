# Baseline Verification

## Stage 0: Initial Setup Verification
Verification that the FastAPI server receives and parses events emitted by the fleet simulator.

## Stage 1: Baseline Ingestion and Storage Verification

### Test Strategy
Emit deterministic sequential events for a single device and verify that running metrics (`count`, `sum`, `avg`, `min`, `max`, `latest_reading`) update accurately.

### Verification Run
```bash
pytest tests/test_baseline.py -v
```
## Stage 2: Event Deduplication Verification

### Test Strategy
Send an event with a unique `event_id`, verify acceptance, and immediately re-send the identical payload. Confirm that the second request returns `is_duplicate: true` and that device counters (`count`, `sum_readings`, `avg_reading`) do not increment.

### Verification Run
```bash
pytest tests/test_deduplication.py -v
```
### Simulator Verification
```bash
python simulate_fleet.py --count 3 --mode duplicates
```
## Stage 3: Out-of-Order Event Handling Verification

### Test Strategy
Send a newer event ($T_2$, value: $100$) followed by an older event ($T_1$, value: $50$, where $T_1 < T_2$). Verify that:
1. The older event is flagged with `is_out_of_order: true`.
2. `latest_reading` remains $100$ and does not regress to $50$.
3. Statistical aggregates (`count`, `sum`, `avg`) correctly incorporate both values.
4. The device history endpoint returns events sorted chronologically by measurement timestamp.

### Verification Run
```bash
pytest tests/test_out_of_order.py -v
```

### Simulator Verification
```bash
python simulate_fleet.py --count 5 --mode out-of-order
```
## Stage 4: Late-Arrival Window Policy Verification

### Test Strategy
1. Send an event with timestamp within the 5-minute sliding window ($T_{\text{now}} - 2\text{m}$). Verify acceptance and aggregate update.
2. Send an event with timestamp beyond the window ($T_{\text{now}} - 10\text{m}$). Verify rejection (`is_late_rejected: true`), increment of `late_rejected_count`, and isolation from aggregate calculations and event logs.

### Verification Run
```bash
pytest tests/test_late_arrival.py -v
```

### Simulator Verification
```bash
python simulate_fleet.py --count 3 --mode delayed
```
## Stage 6: Observability Verification

### Test Strategy
Emit clean, duplicate, out-of-order, and late-arriving events, then scrape `/metrics` to ensure counters increment accurately with bounded low-cardinality labels.

### Verification Run
```bash
pytest tests/test_observability.py -v
```
### Manual Verification Command
```bash
curl http://127.0.0.1:8000/metrics | grep telemetry_
```
---
### Verification Run

Run the complete test suite:

```bash
pytest -v
```
