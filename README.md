# NexusFlow-X

[![CI](https://github.com/srp5166/NexusFlow-X/actions/workflows/ci.yml/badge.svg)](https://github.com/srp5166/NexusFlow-X/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-KRaft-231F20.svg?logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![Spark](https://img.shields.io/badge/Apache_Spark-PySpark-E25A1C.svg?logo=apachespark&logoColor=white)](https://spark.apache.org)

Local-first, Docker-based **streaming data platform**: synthetic events → **Kafka** → **Spark Structured Streaming** → **Parquet** (Bronze → Silver → Gold) → **DuckDB analytics** and **Streamlit dashboard**, with YAML-driven data quality enforcement and quarantine paths.

## Architecture

```mermaid
flowchart LR
  Producer["event_generator\n(synthetic)"] -->|JSON| Kafka["Kafka\nnexusflow-events"]
  Kafka -->|"Spark Streaming"| Bronze["Bronze\n(raw Parquet)"]
  Bronze -->|"flatten + DQ"| Silver["Silver\n(clean Parquet)"]
  Silver -->|"1h window agg"| Gold["Gold\nfact_events_hourly"]
  Silver -->|"out-of-range"| Quarantine["Quarantine\nParquet"]
  Gold -->|"DuckDB read_parquet"| DuckDB["DuckDB\nKPI queries"]
  DuckDB --> Dashboard["Streamlit\ndashboard"]
  Bronze & Silver & Gold -->|"NDJSON"| Metrics["pipeline_metrics.jsonl"]
  Metrics --> Dashboard
```

## Quick start

1. Install [Docker](https://docs.docker.com/get-docker/) with Compose.
2. Clone the repo and run:

   ```bash
   docker compose up -d
   ```

3. Follow **[docs/LOCAL_RUNBOOK.md](docs/LOCAL_RUNBOOK.md)** for topics, `spark-submit`, and the producer.
4. After data lands in Gold, query it or open the dashboard:

   ```bash
   pip install -r requirements.txt
   python analytics/gold_query.py        # CLI KPI report
   streamlit run analytics/dashboard.py  # browser dashboard at localhost:8501
   ```

See **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** for a full 5-minute walkthrough.

**Tests:** `python -m pytest tests/ -q` (also `make test`). CI runs the same on push/PR. PySpark-backed tests are skipped on Python 3.13+ (use 3.10-3.12 or rely on CI).

**Operator shortcuts:** [Makefile](Makefile) -- `make up`, `make bronze`, `make producer`, `make silver`, `make gold`, `make query`, `make dashboard`, `make test`, `make validate`. Use **WSL or Git Bash** on Windows if `make` is not installed.

**Recovery / checkpoints:** [docs/RECOVERY.md](docs/RECOVERY.md)

**Steady progress (14-day plan):** [docs/CONTRIBUTION_PLAN_14D.md](docs/CONTRIBUTION_PLAN_14D.md)

## Layout

| Path | Role |
|------|------|
| `ingestion/` | Producer, event generator, data quality helpers, `quality_rules.yaml` |
| `streaming/` | Bronze, Silver, Gold Spark jobs |
| `analytics/` | DuckDB query layer and Streamlit dashboard |
| `data/` | Parquet output, checkpoints, metrics (generated at runtime, gitignored) |
| `tests/` | Unit + contract tests (pytest) |
| `scripts/` | `spark_submit_*.sh`, `run_gold.sh` helpers |

