# Validation log — local end-to-end run

Recorded proof that the Docker Kafka → Spark Bronze/Silver/Gold → DuckDB/Streamlit path works on a developer machine. Numbers come from `data/metrics/pipeline_metrics.jsonl` and DuckDB over Gold Parquet (both gitignored; regenerate with a local run).

## Run metadata

| Field | Value |
|-------|-------|
| Date | 2026-07-22 |
| Host | Windows 10 + Docker Desktop |
| Stack | Kafka (KRaft), Spark **4.1.2** / Scala 2.13, Kafka connector `spark-sql-kafka-0-10_2.13:4.1.2` |
| Topic | `nexusflow-events` (3 partitions) |
| Gold trigger | `5 minutes` (`processingTime`) |
| Evidence | [assets/dashboard.png](assets/dashboard.png) (Streamlit at screenshot time showed ~20k+ Gold events, **0** pipeline errors) |

## Layer checks

| Layer | Path | Result |
|-------|------|--------|
| Bronze | `data/bronze/` | Parquet present (`part-*.snappy.parquet`) |
| Silver | `data/silver/` | Parquet present |
| Gold | `data/gold/fact_events_hourly/` | Parquet present |
| Checkpoints | `data/checkpoints/{bronze,silver,gold_hourly}/` | Commits / offsets present |
| Quarantine | `data/quarantine/` | No quarantine Parquet this run (synthetic metrics stayed in-range) |
| Metrics | `data/metrics/pipeline_metrics.jsonl` | NDJSON appends for bronze / silver / gold |

## Metrics summary (same session, after dashboard screenshot)

Aggregated from `pipeline_metrics.jsonl` (`error` null on every line):

| Layer | Batches | Rows written (sum of batch `row_count`) | Errors |
|-------|---------|------------------------------------------|--------|
| Bronze | 175 | 39,060 | **0** |
| Silver | 129 | 38,590 | **0** |
| Gold | 27 | (hourly aggregate rows per batch) | **0** |

DuckDB over Gold Parquet after the same session:

```text
sum(event_count) ≈ 49,995   # continued producing after the README screenshot
distinct event_type = 6
```

Screenshot vs this log: the PNG was taken mid-run (~20k–23k Gold events). Leaving the producer and jobs up longer only increases volume; health stayed at **0 errors**.

## What is guaranteed vs not guaranteed

**Guaranteed for this local stack (when commands succeed):**

- Bronze resumes Kafka offsets from `data/checkpoints/bronze` after a clean Spark restart.
- Silver / Gold file-stream checkpoints track which Parquet files were already processed.
- Out-of-range Silver rows land under `data/quarantine/` when quality rules fire.
- Each successful micro-batch appends one NDJSON metrics line (`layer`, `batch_id`, `row_count`, `error`).

**Not guaranteed (see also [RECOVERY.md](RECOVERY.md)):**

- No SLA for recovery time or exactly-once end-to-end delivery.
- Multi-broker Kafka, cloud deploy, Airflow, Grafana, and production monitoring are out of scope — [ROADMAP.md](ROADMAP.md).
- Exact duplicate behavior after partial deletes of checkpoints vs Parquet requires inspecting Spark checkpoint metadata.

## How to reproduce

Follow [LOCAL_RUNBOOK.md](LOCAL_RUNBOOK.md) or [DEMO_SCRIPT.md](DEMO_SCRIPT.md). For a bounded producer burst (then exit):

```bash
python -m ingestion.producer --batches 30
# or inside Docker:
docker exec nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && python3 -m ingestion.producer --batches 30'
```

Then open the dashboard (`make dashboard` / `python -m streamlit run analytics/dashboard.py`) and confirm Gold KPIs and **0** errors in pipeline health.
