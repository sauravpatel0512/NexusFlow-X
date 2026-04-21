# NexusFlow-X — local runbook

Run everything from the **repository root**. Data lands under **`data/`** on the host (mounted as **`/app/data`** in `nexus-spark`).

**Governance:** [.specify/memory/constitution.md](../.specify/memory/constitution.md)

## Prerequisites

- Docker Desktop (or Docker Engine) with Compose
- Ports **9092**, **29092**, **4040** available on the host (see [Port conflicts](#port-conflicts) if something else is listening)

### Windows and WSL

- **PowerShell / CMD:** Use the `docker` and `docker exec` commands in this doc as shown. Paths like `data/bronze` are under the repo root on your drive.
- **WSL2:** Clone or access the repo on the **Linux filesystem** (`~/...`) when possible so file I/O and line endings match Linux; if the repo lives on `/mnt/c/...`, watch for CRLF issues on shell scripts (see [Troubleshooting](#troubleshooting)).
- **`make`:** Not installed by default on Windows; use **Git Bash**, **WSL**, or run the equivalent `docker compose` / `docker exec` commands from this runbook.

## Environment

| Variable | Purpose |
|----------|---------|
| `NEXUSFLOW_DATA_ROOT` | Override data directory (default: `/app/data` in Docker, `./data` locally) |
| `QUALITY_RULES_PATH` | Override path to `quality_rules.yaml` |
| `KAFKA_BOOTSTRAP_SERVERS` | Spark jobs: default `kafka:9092` in Docker, `127.0.0.1:29092` on host |
| `KAFKA_BROKER` | Producer: same convention |

**Ivy / `--packages`:** The Spark image sets `JAVA_TOOL_OPTIONS=-Duser.home=/tmp` so Kafka connector JARs resolve. If you run `spark-submit` from a shell that injects a bad `HOME`, run `export HOME=/tmp` first.

## Makefile (optional)

From the repo root (Linux / WSL / Git Bash), **`make up`**, **`make bronze`**, **`make producer`**, **`make silver`**, **`make gold`**, **`make test`**, **`make validate`** wrap the same Docker commands without `-it` (better for scripts). On Windows without `make`, use the `docker` / `docker exec` commands below.

## 1. Start the stack

```bash
docker compose up -d
```

Services: `kafka` (KRaft), `nexus-spark` (Spark + repo at `/app`), network `nexus-net`.

### Verify the stack

From the repo root:

```bash
docker compose ps
```

You should see **`kafka`** and **`nexus-spark`** with state **running** (or **running (healthy)** if a healthcheck is present). Quick log peek if Kafka is slow to start:

```bash
docker compose logs kafka --tail 30
```

If `docker compose ps` shows **Exit** or **restarting**, fix that before running Spark jobs—usually a port bind failure or an old container name conflict (`docker compose down` then `up -d` again after freeing ports).

## 2. Kafka topic

Topic **`nexusflow-events`** should exist. If not:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic nexusflow-events --partitions 3 --replication-factor 1
```

## 3. Bronze (Kafka → Parquet)

In **`nexus-spark`** (requires Kafka connector):

```bash
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_bronze.sh'
```

Or one-liner:

```bash
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && /opt/spark/bin/spark-submit --master local[2] --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1 streaming/bronze_stream.py'
```

## 4. Producer

**Inside the same Docker network** (recommended):

```bash
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && python3 -m ingestion.producer'
```

**From the host** (outside Docker):

```bash
pip install -r requirements.txt
python -m ingestion.producer
```

Uses **`127.0.0.1:29092`** by default.

## 5. Silver (Bronze Parquet → Silver Parquet)

Requires Bronze output under `data/bronze/`. Run:

```bash
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_silver.sh'
```

## 6. Gold (Silver → hourly aggregates)

Requires Silver under `data/silver/`. Uses a **5-minute** processing trigger; allow several minutes for output.

```bash
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_gold.sh'
```

From **PowerShell** (same `docker exec` pattern as other sections):

```powershell
docker exec -it nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && /opt/spark/bin/spark-submit --master local[2] --driver-memory 2g streaming/gold_aggregations.py'
```

From **WSL**:

```bash
bash scripts/run_gold.sh
```

## 7. Verify outputs

| Layer | Path (container) | Path (host) |
|-------|------------------|-------------|
| Bronze | `/app/data/bronze` | `data/bronze` |
| Silver | `/app/data/silver` | `data/silver` |
| Gold | `/app/data/gold/fact_events_hourly` | `data/gold/fact_events_hourly` |
| Checkpoints | `/app/data/checkpoints/<layer>` | `data/checkpoints/<layer>` |
| Quarantine | `/app/data/quarantine/...` | `data/quarantine/...` |
| Metrics | `/app/data/metrics/pipeline_metrics.jsonl` | `data/metrics/pipeline_metrics.jsonl` |

Each successful Bronze/Silver/Gold micro-batch appends one **NDJSON** line (`layer`, `batch_id`, `row_count`, optional `error`). Tail with: `Get-Content data/metrics/pipeline_metrics.jsonl -Tail 20` (PowerShell) or `tail -f data/metrics/pipeline_metrics.jsonl` (WSL). The `data/metrics/` tree is gitignored.

Spark UI: **http://localhost:4040** while a job is running.

**Restarts / checkpoints / reset:** [RECOVERY.md](RECOVERY.md).

## 8. Stack versions (reference)

- Spark **4.0.1**, Scala **2.13** (from `spark:python3` image)
- Kafka connector package: **`org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.1`**

See [validation-log.md](validation-log.md) for a recorded validation run.

## Troubleshooting

### Port conflicts

Symptoms: `docker compose up` fails with **address already in use** / **bind** errors for **9092**, **29092**, or **4040**.

1. Stop anything that claimed those ports (another Kafka, local Spark UI, or a stale compose stack): `docker compose down` in this repo, then retry `docker compose up -d`.
2. On **Windows**, find the owning PID, then stop the process or change its config:

   ```powershell
   netstat -ano | findstr :9092
   netstat -ano | findstr :29092
   netstat -ano | findstr :4040
   ```

   The last column is the PID; end it from Task Manager or `taskkill /PID <pid> /F` only if you know it is safe.
3. If you **must** keep another service on a port, edit host port mappings in [`docker-compose.yml`](../docker-compose.yml) and set `KAFKA_BOOTSTRAP_SERVERS` / `KAFKA_BROKER` to match your new **host** listener for the producer and Spark jobs.

- **`set: pipefail` / `invalid option name` when running `scripts/*.sh` in the container:** The script likely has **Windows CRLF** line endings. Scripts in this repo must use **LF** only (see `.gitattributes`). Re-save the file as LF, or run `sed -i 's/\r$//' scripts/spark_submit_bronze.sh` from WSL on the repo copy under `/mnt/c/...`.
- **Gold fails with `Failed to parse time string` on `maxFileAge`:** Spark 4 expects durations like **`600s`** or **`10min`**, not **`10 min`** (space). See [streaming/gold_aggregations.py](../streaming/gold_aggregations.py).
- **Gold “no files yet”:** The job triggers every **5 minutes**; wait at least one full interval before checking `data/gold/fact_events_hourly/`.

## Future / not in this repo

Cloud deploy, Kubernetes, Airflow, Grafana, and full production monitoring are **out of scope** for the local stack. See [specs/production-implementation/ROADMAP.md](../specs/production-implementation/ROADMAP.md).
