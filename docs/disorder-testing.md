# Disorder & Chaos Testing

This document details the mixed-disorder validation suite simulating realistic sensor network failure modes (simultaneous arrival jitter, out-of-order delivery, network packet duplicates, and stale delayed timestamps).

## Test Scenario: Mixed Disorder Ingestion

### Ground Truth Setup
Target device: `sensor-chaos-001`

| Event ID | Event Timestamp ($T$) | Reading | Condition | Expected Outcome |
|---|---|---|---|---|
| `evt-chaos-a` | $T_{\text{now}} - 60\text{s}$ | 20.0 | Valid Measurement | Accepted |
| `evt-chaos-b` | $T_{\text{now}} - 40\text{s}$ | 30.0 | Valid Measurement | Accepted |
| `evt-chaos-c` | $T_{\text{now}} - 20\text{s}$ | 25.0 | Newest Valid Measurement | Accepted (Defines Latest State) |
| `evt-chaos-d-late` | $T_{\text{now}} - 10\text{m}$ | 999.0 | Stale ($> 5\text{m}$ window) | Late Rejected |

### Arrival Sequence
The events are delivered in randomized, shuffled order with duplicates injected:

$$\text{Delivery Stream: } [C \rightarrow A \rightarrow D_{\text{late}} \rightarrow C_{\text{dup}} \rightarrow B \rightarrow A_{\text{dup}}]$$

1. **Step 1 ($C$):** Ingested first. Timestamp is $T-20\text{s}$. Sets `latest_reading = 25.0`.
2. **Step 2 ($A$):** Arrives with timestamp $T-60\text{s} < T-20\text{s}$. Flagged as `is_out_of_order: true`. Historical aggregates incorporate value $20.0$, but `latest_reading` remains $25.0$.
3. **Step 3 ($D_{\text{late}}$):** Arrives with timestamp $T-10\text{m}$. Exceeds the 5-minute late-arrival threshold. Flagged as `is_late_rejected: true`. Dropped from aggregates.
4. **Step 4 ($C_{\text{dup}}$):** Duplicate of event $C$. Matched in TTL deduplication index. Flagged as `is_duplicate: true`. Aggregate computation bypassed.
5. **Step 5 ($B$):** Arrives with timestamp $T-40\text{s} < T-20\text{s}$. Flagged as `is_out_of_order: true`. Historical aggregates incorporate value $30.0$, latest reading remains $25.0$.
6. **Step 6 ($A_{\text{dup}}$):** Duplicate of event $A$. Flagged as `is_duplicate: true`. Bypassed.

### Final Correctness Assertion
Despite chaotic arrival ordering and invalid data injection, the final stored state matches the mathematically computed ground truth:

```json
{
  "device_id": "sensor-chaos-001",
  "count": 3,
  "sum_readings": 75.0,
  "avg_reading": 25.0,
  "min_reading": 20.0,
  "max_reading": 30.0,
  "latest_reading": 25.0,
  "out_of_order_count": 2,
  "late_rejected_count": 1
}
```
The ordered historical journal strictly sorted the events as 
`[evt-chaos-a, evt-chaos-b, evt-chaos-c]`
### Verification Execution
```bash
pytest tests/test_disorder.py -v.
```
## Observability During Disorder Testing

During chaotic ingestion runs, the `/metrics` endpoint exposes runtime counters reflecting network anomalies:

```promql
# Sample metrics scraped during disorder execution
telemetry_events_ingested_total{status="accepted"} 3.0
telemetry_events_ingested_total{status="duplicate_ignored"} 2.0
telemetry_events_ingested_total{status="late_rejected"} 1.0
telemetry_events_disorder_total{type="out_of_order"} 2.0
telemetry_events_disorder_total{type="late_arrival"} 1.0
telemetry_events_disorder_total{type="duplicate"} 2.0
telemetry_active_devices_total 1.0
```
