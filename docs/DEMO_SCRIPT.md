# NexusFlow-X -- demo walkthrough (~5 minutes with gold-fast)

Run this on **WSL / Linux** (or Git Bash) from the repo root. Docker Desktop must be running.

## 1. Start the stack

```bash
make up            # docker compose up -d + create topic nexusflow-events
docker ps          # expect: kafka, nexus-spark running
```

## 2. Ingest (Bronze)

Open **two terminals**.

Terminal 1 -- Bronze streaming job:

```bash
make bronze
```

Terminal 2 -- produce a bounded burst of synthetic events (then exits):

```bash
make producer ARGS='--batches 30'
# equivalent: docker exec nexus-spark bash -c 'cd /app && export PYTHONPATH=/app && python3 -m ingestion.producer --batches 30'
```

Wait ~30 seconds, then verify:

```bash
ls data/bronze/
# expect: part-*.snappy.parquet files
ls data/checkpoints/bronze/
# expect: commits/, offsets/, sources/
```

Without `ARGS`, `make producer` runs forever (10 events/sec); stop with `Ctrl+C`. Use `--once` for a single batch.

**Optional — JSON Schema / DLQ demo:** inject poison payloads, then confirm depth in the dashboard (Data quality snapshot) or CLI:

```bash
make producer ARGS='--inject-poison 5 --once'
make dlq ARGS='-n 5'
# refresh Streamlit: Kafka DLQ messages metric should be >= 5
```

## 3. Transform (Silver)

```bash
make silver
```

Wait ~20 seconds, then verify:

```bash
ls data/silver/
# expect: part-*.snappy.parquet
ls data/quarantine/silver/
# expect: parquet files if any out-of-range records were quarantined
```

Stop Silver with `Ctrl+C` after a few batches.

## 4. Aggregate (Gold)

```bash
make gold-fast     # GOLD_PROCESSING_TIME=1 minute (default make gold waits ~5 min)
```

Gold with `gold-fast` triggers every **1 minute**. Wait ~90 seconds, then verify:

```bash
ls data/gold/fact_events_hourly/
# expect: part-*.snappy.parquet
```

Stop Gold with `Ctrl+C` after verifying output.

## 5. Query Gold (DuckDB)

From the **host** (outside Docker):

```bash
pip install -r requirements.txt   # one-time: adds duckdb
python analytics/gold_query.py
```

Expected output:

```
============================================================
NexusFlow-X  Gold KPI Report
============================================================

Total events (Gold): 1,234

--- KPIs by event_type ---
   event_type  total_events  avg_distance  avg_temperature  avg_amount
  trip_start           210         48.12            15.30      245.60
    trip_end           195         51.40            14.80      230.15
         ...

--- Hourly volume ---
 hour  events
    0     102
    1      87
  ...

--- Pipeline batch metrics ---
  bronze: 5 batches, 500 rows, 0 errors
  silver: 4 batches, 480 rows, 0 errors
  gold: 2 batches, 120 rows, 0 errors
```

(Exact numbers depend on producer run time and event randomness.)

## 6. Dashboard

```bash
make dashboard     # python -m streamlit run analytics/dashboard.py
```

Open [http://localhost:8501](http://localhost:8501) in a browser. You should see four panels: hourly volume bar chart, KPIs by event type, pipeline health timeline, and data quality snapshot.

Screenshot for the README lives at [`docs/assets/dashboard.png`](assets/dashboard.png).

## 7. Failure and recovery

Demonstrate checkpoint-based resume:

```bash
# In terminal 1: start Bronze
make bronze
# In terminal 2: produce events
make producer ARGS='--batches 20'
# Wait 15 seconds, then kill Bronze with Ctrl+C
# Restart Bronze:
make bronze
# Produce more events:
make producer ARGS='--batches 20'
```


Verify that Bronze picks up from the last checkpoint (no duplicate processing of already-committed offsets). Check `data/checkpoints/bronze/commits/` -- the commit number increments across restarts.

## 8. Bad data and quarantine

Check quarantine output:

```bash
ls data/quarantine/silver/
```

Check metrics for errors:

```bash
tail -5 data/metrics/pipeline_metrics.jsonl
```

Any batch with `"error":` in the NDJSON line indicates a processing failure. The dashboard also surfaces these in the "Data quality snapshot" panel.

---

**Total time:** ~4--6 minutes with `make gold-fast` (1-minute Gold trigger). Default `make gold` waits ~5 minutes per micro-batch — see `GOLD_PROCESSING_TIME` in [LOCAL_RUNBOOK.md](LOCAL_RUNBOOK.md).
