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
