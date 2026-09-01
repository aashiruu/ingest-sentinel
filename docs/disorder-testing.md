# Disorder & Chaos Testing

This document details both the deterministic unit-level validation and the high-volume fleet chaos simulation under realistic sensor network failure modes (arrival jitter, out-of-order delivery, packet duplicates, and stale delayed timestamps).

---

## 1. Deterministic Ground Truth Verification (Unit Level)

This test executes an isolated 6-event sequence against device `sensor-chaos-001` to mathematically prove that duplicate filtering, watermark rejection, and event-time ordering behave correctly.

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
pytest tests/test_disorder.py -v
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
## 2. High-Volume Fleet Chaos Simulation (Live Dashboard Burst)
To observe metric behavior under continuous load, the device fleet simulator was configured to stream **2,500+ randomized events** with aggressive temporal shuffling, duplicate injections, and delayed packets across 3 active sensors.
### Fleet Simulator Command
```bash
python simulate_fleet.py --count 100 --mode disorder
```
## Dashboard Evidence Under Chaos

During high-volume fleet disorder bursts, the Grafana dashboard visualizes real-time metric categorization and disorder tracking across three specific observation areas:

### 1. Full Dashboard Overview
<img width="1006" height="491" alt="Disorder Test Dashboard Overview" src="https://github.com/user-attachments/assets/c86a1abb-d1cf-4cae-8416-de33d0b07239" />

### 2. Ingestion Status Breakdown
Tracks throughput of accepted events versus discarded duplicates and late-rejected stale payloads.

<img width="511" height="276" alt="Ingested Events by Status" src="https://github.com/user-attachments/assets/f7ce1da4-d7d1-4bd4-98c3-6447bb91b596" />


### 3. Anomaly Classification
Demonstrates the detection curve of out-of-order arrivals and retransmission duplicates during load spikes.

<img width="506" height="290" alt="Disorder Anomalies Breakdown" src="https://github.com/user-attachments/assets/aecf8695-4156-4145-9e16-46df96da7f8e" />

### 4. Bounded Fleet Cardinality
Confirms that the device tracking gauge remains constant at 3 devices without label explosion.

<img width="504" height="271" alt="active devices" src="https://github.com/user-attachments/assets/2cda8695-1493-4932-8042-385e9ede8cdf" />
