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
