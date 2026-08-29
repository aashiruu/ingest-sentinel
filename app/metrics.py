from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Ingestion throughput categorized by disposition status
EVENTS_INGESTED_TOTAL = Counter(
    "telemetry_events_ingested_total",
    "Total number of telemetry events processed by disposition status",
    ["status"]  # 'accepted', 'duplicate_ignored', 'late_rejected'
)

# Disorder occurrences categorized by anomaly type
EVENTS_DISORDER_TOTAL = Counter(
    "telemetry_events_disorder_total",
    "Total count of telemetry disorder anomalies observed",
    ["type"]  # 'out_of_order', 'late_arrival', 'duplicate'
)

# Active devices tracked in memory
ACTIVE_DEVICES_GAUGE = Gauge(
    "telemetry_active_devices_total",
    "Total count of unique devices registered in active state memory"
)
