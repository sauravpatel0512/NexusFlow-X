# Production roadmap (out of scope for this repo)

NexusFlow-X is a **local-first** portfolio / learning stack: Docker Compose, single-broker Kafka (KRaft), Spark Structured Streaming on one container, Parquet on a bind-mounted `data/` directory, DuckDB + Streamlit for analytics.

The items below are **explicitly not implemented** here. They are a map of what a production cut would add—not a commitment or timeline.

## Near-term hardening (local)

| Item | Status |
|------|--------|
| Topic auto-create / bootstrap script | Done — `scripts/create_topic.sh` + `make topic` / `make up` (events + DLQ) |
| Faster demo Gold trigger (documented toggle) | Done — `GOLD_PROCESSING_TIME` / `make gold-fast` |
| Pinned deps + lint in CI | Done — `requirements.txt` + ruff |
| JSON Schema contract + Kafka DLQ | Done — `ingestion/event_schema.json`, producer gate, `nexusflow-events-dlq`, `make dlq` / `--inject-poison` |
| Bronze parse-failure quarantine | Done — `data/quarantine/bronze_parse/` for null/`from_json` failures |
| Formal load / failure injection scripts | Partial — `--inject-poison` covers schema poison; load soak scripts not started |

## Production-shaped (not in this repo)

| Area | Examples |
|------|----------|
| Orchestration | Airflow / Prefect / Dagster for job lifecycle beyond long-running `spark-submit` |
| Cloud runtime | Managed Kafka, EMR / Dataproc / Databricks, object storage (S3/GCS/ADLS) |
| Kubernetes | Deploy Spark / Kafka / dashboards with secrets, HPA, network policies |
| Observability | Prometheus metrics, Grafana dashboards, structured log shipping, alerting |
| Governance | Catalog, lineage, IAM, PII controls, multi-tenant isolation |
| Delivery SLAs | Exactly-once sinks, multi-AZ Kafka, Confluent Schema Registry / Avro, formal RTO/RPO |

Local DLQ + JSON Schema (above) is a learning stand-in—not multi-AZ replay or registry-backed contracts.

## What stays true locally

- Medallion layers (Bronze → Silver → Gold) with checkpoints and quarantine.
- JSON Schema producer gate + Kafka DLQ topic for poison messages.
- YAML-driven quality rules and NDJSON batch metrics.
- Analytics over Gold Parquet without a separate warehouse service.

For how to run and recover the **current** stack, see [LOCAL_RUNBOOK.md](LOCAL_RUNBOOK.md) and [RECOVERY.md](RECOVERY.md). For a recorded successful run, see [validation-log.md](validation-log.md).
