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
