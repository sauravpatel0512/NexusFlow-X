"""Streamlit dashboard for Gold KPIs and pipeline metrics.

  python -m streamlit run analytics/dashboard.py
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from analytics.gold_query import load_metrics_lines, metrics_summary
from ingestion.quarantine_stats import quarantine_breakdown, sum_parse_failures

st.set_page_config(page_title="NexusFlow-X", layout="wide")

_DATA_ROOT = Path(os.getenv("NEXUSFLOW_DATA_ROOT", Path(__file__).resolve().parent.parent / "data"))
_GOLD_DIR = _DATA_ROOT / "gold" / "fact_events_hourly"
_QUARANTINE_DIR = _DATA_ROOT / "quarantine"
_GOLD_GLOB = str(_GOLD_DIR / "*.parquet")

_gold_exists = _GOLD_DIR.exists() and any(_GOLD_DIR.glob("*.parquet"))

st.title("NexusFlow-X Pipeline Dashboard")
st.caption("Kafka -> Spark Bronze/Silver/Gold -> DuckDB / Streamlit")

if not _gold_exists:
    st.warning(
        "No Gold Parquet files found. Run the full pipeline first "
        "(see docs/LOCAL_RUNBOOK.md) then refresh this page."
    )

st.header("Event volume by hour")

con = None
if _gold_exists:
    import duckdb

    con = duckdb.connect()

    df_hourly = con.sql(f"""
        SELECT hour, sum(event_count) AS events
        FROM read_parquet('{_GOLD_GLOB}')
        GROUP BY hour ORDER BY hour
    """).fetchdf()

    st.bar_chart(df_hourly, x="hour", y="events", use_container_width=True)
else:
    st.info("Waiting for Gold data.")

st.header("Average metrics by event type")

if _gold_exists and con is not None:
    df_kpi = con.sql(f"""
        SELECT
            event_type,
            sum(event_count)              AS total_events,
            round(avg(avg_distance), 2)   AS avg_distance,
            round(avg(avg_temperature), 2) AS avg_temperature,
            round(avg(avg_amount), 2)     AS avg_amount,
            round(avg(avg_duration), 2)   AS avg_duration
        FROM read_parquet('{_GOLD_GLOB}')
        GROUP BY event_type
        ORDER BY total_events DESC
    """).fetchdf()

    col1, col2 = st.columns([1, 2])
    with col1:
        total = int(df_kpi["total_events"].sum())
        st.metric("Total Gold events", f"{total:,}")
    with col2:
        st.dataframe(df_kpi, use_container_width=True, hide_index=True)
else:
    st.info("Waiting for Gold data.")

st.header("Pipeline health")

lines = load_metrics_lines()
if lines:
    summary = metrics_summary(lines)
    cols = st.columns(len(summary))
    for col_widget, (layer, stats) in zip(cols, summary.items(), strict=True):
        col_widget.metric(f"{layer} batches", stats["batches"])
        col_widget.metric(f"{layer} rows", f"{stats['rows']:,}")
        col_widget.metric(f"{layer} errors", stats["errors"])

    df_timeline = pd.DataFrame(lines)
    df_timeline["timestamp"] = df_timeline["ts"].apply(
        lambda t: datetime.fromtimestamp(t) if t else None
    )
    df_timeline = df_timeline.dropna(subset=["timestamp"])
    if not df_timeline.empty:
        st.subheader("Rows processed over time")
        chart_data = (
            df_timeline.groupby(["timestamp", "layer"])["row_count"]
            .sum()
            .reset_index()
            .pivot(index="timestamp", columns="layer", values="row_count")
            .fillna(0)
        )
        st.line_chart(chart_data, use_container_width=True)
else:
    st.info("No pipeline metrics yet (data/metrics/pipeline_metrics.jsonl).")

st.header("Data quality snapshot")

breakdown = quarantine_breakdown(_DATA_ROOT)
parse_failures = sum_parse_failures(lines)
total_q_files = sum(stats["files"] for stats in breakdown.values())

st.subheader("Quarantine by layer")
layer_cols = st.columns(max(len(breakdown), 1))
for col_widget, (layer, stats) in zip(layer_cols, breakdown.items(), strict=True):
    col_widget.metric(f"{layer} files", stats["files"])

pcol, tcol, dcol = st.columns(3)
with pcol:
    st.metric("Bronze parse_failures (metrics)", f"{parse_failures:,}")
    st.caption("Sum of extra.parse_failures from pipeline_metrics.jsonl")
with tcol:
    st.metric("Quarantine Parquet files", total_q_files)
    if total_q_files and _gold_exists and con is not None:
        q_glob = str(_QUARANTINE_DIR / "**" / "*.parquet")
        try:
            q_count = con.sql(f"SELECT count(*) FROM read_parquet('{q_glob}')").fetchone()[0]
            st.metric("Quarantine rows (total)", f"{q_count:,}")
        except Exception:
            st.caption("Could not read quarantine parquet files.")
with dcol:
    try:
        from ingestion.dlq_stats import fetch_dlq_depth

        depth, dlq_err = fetch_dlq_depth()
        if depth is not None:
            st.metric("Kafka DLQ messages", f"{depth:,}")
            if dlq_err:
                st.caption(dlq_err)
        else:
            st.metric("Kafka DLQ messages", "—")
            st.caption(dlq_err or "Kafka unreachable")
    except Exception as ex:
        st.metric("Kafka DLQ messages", "—")
        st.caption(f"DLQ stats unavailable: {ex}")

if lines:
    error_lines = [m for m in lines if m.get("error")]
    if error_lines:
        st.warning(f"{len(error_lines)} batch(es) recorded errors.")
        with st.expander("Error details"):
            for m in error_lines[-10:]:
                st.text(f"[{m.get('layer')}] batch {m.get('batch_id')}: {m.get('error')}")
    else:
        st.success("No batch errors recorded.")
else:
    st.info("No metrics data yet.")
