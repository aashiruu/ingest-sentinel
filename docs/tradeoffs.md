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

## 2. Deduplication Strategy: TTL-Bounded Deduplication Cache

### Context
In IoT systems operating over cellular or lossy networks, client retries cause identical payloads (same `event_id`) to arrive multiple times. Ingestion pipelines must guarantee idempotency so duplicate deliveries do not distort statistical aggregates.

### Options Considered
1. **Unbounded Primary Key Set:**
   - *Pros:* Perfect deduplication guarantee across the lifetime of the service.
   - *Cons:* Unbounded memory growth ($O(N)$ space complexity) leading to eventual out-of-memory crashes.
2. **Bloom Filter / Probabilistic Filter:**
   - *Pros:* Constant memory footprint for high volumes.
   - *Cons:* False positives can cause genuine distinct events to be discarded; no expiration mechanism without complex scalable filter rotation.
3. **TTL-Bounded Deduplication Set with Eviction (Selected):**
   - *Pros:* Keeps memory bounded ($O(K)$ where $K$ is event volume within the deduplication window). Sufficient for network retry jitter.
   - *Cons:* Extreme duplicates arriving beyond the TTL window could be reprocessed if older than the eviction boundary (mitigated by combining with the late-arrival policy in Stage 4).

### Decision
Implement an in-memory deduplication index tracking `event_id -> ingested_at` timestamps. Duplicate arrivals within the active retention window are acknowledged idempotently without mutating aggregates.

## 3. Out-of-Order Handling: Event-Time Ordering vs. Arrival-Time State

### Context
Network routing variations and device connection drops mean events regularly arrive out of sequence. An event generated at 10:00:00 might reach the API after an event generated at 10:00:10.

### Options Considered
1. **Drop Out-of-Order Arrivals:**
   - *Pros:* Simple ingestion path; state only moves strictly forward in time.
   - *Cons:* Destructive data loss; invalidates aggregate volume metrics and historical sensor trends.
2. **Event-Time Ordering with Isolated Latest-State Guards (Selected):**
   - *Pros:* Decouples aggregate computation from the current physical status. Older arrivals are incorporated into cumulative statistics and inserted into the sorted journal, but guarded from overwriting `latest_reading`.
   - *Cons:* Requires maintaining timestamp comparisons during ingestion and sorting the underlying event history.

### Decision
Guards evaluate `event.timestamp >= aggregate.latest_timestamp` before updating the latest device reading. Historical aggregates seamlessly assimilate out-of-order events into the dataset.

## 4. Late-Arrival Window Policy: Watermark & Bounded Lateness

### Context
Allowing arbitrary retroactive data mutation leads to unbounded memory retention and unstable historical analytics. Stream processing and ingestion architectures require a definitive cut-off window (watermark) after which data is considered finalized.

### Options Considered
1. **Unbounded Late Acceptance:**
   - *Pros:* Accommodates offline sensor devices that reconnect after weeks.
   - *Cons:* Destabilizes materialized reporting; prevents cache eviction and memory compaction.
2. **Fixed Sliding Lateness Window (Selected):**
   - *Pros:* Provides deterministic finality for aggregates; bounds deduplication cache lifetimes; explicitly isolates stale data.
   - *Cons:* Legitimate measurements recorded during extended network blackouts exceeding the window are rejected at the primary tier (would require secondary batch backfilling in production pipelines).

### Decision
Enforce a configurable 5-minute (300s) late-arrival window evaluated against current ingestion time. Events with timestamps older than 300s are rejected with `late_rejected` status and tracked in dead-letter counters without altering device state.

## 5. Metric Cardinality: Platform Aggregation vs. Per-Device Dimensions

### Context
Telemetry services process millions of events across large device fleets. Ingested events undergo classification into accepted, duplicate, out-of-order, and late-rejected states.

### Options Considered
1. **Per-Device Prometheus Labels:**
   - *Pros:* Allows filtering Prometheus dashboards down to an individual device ID.
   - *Cons:* Creates an unbounded metric cardinality explosion ($O(N \times \text{metrics})$), degrading Prometheus TSDB performance and driving high memory usage.
2. **Aggregated Low-Cardinality Metric Counters (Selected):**
   - *Pros:* Constant metric time-series count ($O(1)$) regardless of fleet size. High throughput and predictable memory footprint.
   - *Cons:* Individual device debugging relies on query endpoints (`/api/v1/devices/{id}`) rather than global Prometheus metrics.

### Decision
Export bounded Prometheus counters representing global operational states (`telemetry_events_ingested_total{status}`, `telemetry_events_disorder_total{type}`). Per-device debugging is delegated to endpoint lookups and localized event history logs.
