# Production roadmap (out of scope for this repo)

NexusFlow-X is a **local-first** portfolio / learning stack: Docker Compose, single-broker Kafka (KRaft), Spark Structured Streaming on one container, Parquet on a bind-mounted `data/` directory, DuckDB + Streamlit for analytics.

The items below are **explicitly not implemented** here. They are a map of what a production cut would add—not a commitment or timeline.

## Near-term hardening (still local)

| Item | Why |
|------|-----|
| Topic auto-create / bootstrap script | First-run friction for new clones |
| Faster demo Gold trigger (documented toggle) | Shorter walkthroughs without editing source |
| Pinned deps + lint in CI | Reproducible packaging |
| Formal load / failure injection scripts | Stronger demo of quarantine + recovery |

## Production-shaped (not in this repo)

| Area | Examples |
|------|----------|
| Orchestration | Airflow / Prefect / Dagster for job lifecycle beyond long-running `spark-submit` |
| Cloud runtime | Managed Kafka, EMR / Dataproc / Databricks, object storage (S3/GCS/ADLS) |
| Kubernetes | Deploy Spark / Kafka / dashboards with secrets, HPA, network policies |
| Observability | Prometheus metrics, Grafana dashboards, structured log shipping, alerting |
| Governance | Catalog, lineage, IAM, PII controls, multi-tenant isolation |
| Delivery SLAs | Exactly-once sinks, DLQ policies, multi-AZ Kafka, formal RTO/RPO |

## What stays true locally

- Medallion layers (Bronze → Silver → Gold) with checkpoints and quarantine.
- YAML-driven quality rules and NDJSON batch metrics.
- Analytics over Gold Parquet without a separate warehouse service.

For how to run and recover the **current** stack, see [docs/LOCAL_RUNBOOK.md](../../docs/LOCAL_RUNBOOK.md) and [docs/RECOVERY.md](../../docs/RECOVERY.md). For a recorded successful run, see [docs/validation-log.md](../../docs/validation-log.md).
