# Design Trade-offs & Decisions

This document records the design choices and architectural trade-offs evaluated during development.

## 1. Storage Strategy: Materialized State with In-Memory Event Journal

### Context
Telemetry ingestion systems must serve current device status (`latest reading`) and aggregate metrics (mean, count, min/max) without scanning the entire historical dataset on every request.

### Options Considered
1. **Raw Event Log with On-Demand Aggregation:**
   - *Pros:* Trivially simple ingestion path; no state synchronization required.
   - *Cons:* Read performance degrades linearly ($O(N)$) as event volume scales.
2. **Materialized State with Event Journal (Selected):**
   - *Pros:* Ingestion updates running counters and tracks the latest event chronologically; reads for current state and aggregate summaries execute in $O(1)$ time. Preserves event history per device for retroactive adjustments.
   - *Cons:* Requires atomic state mutations to prevent race conditions during concurrent ingestion.

### Decision
Adopt an in-memory hybrid store combining a per-device event log (sorted by timestamp) and a materialized device state record (`count`, `sum`, `avg`, `min`, `max`, `latest_timestamp`, `latest_reading`).
