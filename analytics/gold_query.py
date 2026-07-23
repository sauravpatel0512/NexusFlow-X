"""DuckDB queries over Gold Parquet and pipeline_metrics.jsonl.

  python analytics/gold_query.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb


def _data_root() -> Path:
    import os

    env = os.getenv("NEXUSFLOW_DATA_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data"


def _gold_path() -> str:
    return str(_data_root() / "gold" / "fact_events_hourly" / "*.parquet")


def _metrics_path() -> Path:
    return _data_root() / "metrics" / "pipeline_metrics.jsonl"


def total_events(con: duckdb.DuckDBPyConnection | None = None) -> int:
    con = con or duckdb.connect()
    row = con.sql(
        f"SELECT coalesce(sum(event_count), 0) AS total FROM read_parquet('{_gold_path()}')"
    ).fetchone()
    return int(row[0])


def kpis_by_event_type(con: duckdb.DuckDBPyConnection | None = None):
    con = con or duckdb.connect()
    return con.sql(f"""
        SELECT
            event_type,
            sum(event_count)        AS total_events,
            round(avg(avg_distance), 2)    AS avg_distance,
            round(avg(avg_temperature), 2) AS avg_temperature,
            round(avg(avg_amount), 2)      AS avg_amount
        FROM read_parquet('{_gold_path()}')
        GROUP BY event_type
        ORDER BY total_events DESC
    """).fetchdf()


def hourly_volume(con: duckdb.DuckDBPyConnection | None = None):
    con = con or duckdb.connect()
    return con.sql(f"""
        SELECT
            hour,
            sum(event_count) AS events
        FROM read_parquet('{_gold_path()}')
        GROUP BY hour
        ORDER BY hour
    """).fetchdf()


def load_metrics_lines() -> list[dict]:
    p = _metrics_path()
    if not p.exists():
        return []
    lines: list[dict] = []
    for raw in p.read_text(encoding="utf-8").strip().splitlines():
        try:
            lines.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return lines


def metrics_summary(lines: list[dict] | None = None) -> dict:
    lines = lines if lines is not None else load_metrics_lines()
    summary: dict[str, dict] = {}
    for m in lines:
        layer = m.get("layer", "unknown")
        if layer not in summary:
            summary[layer] = {"batches": 0, "rows": 0, "errors": 0}
        summary[layer]["batches"] += 1
        summary[layer]["rows"] += m.get("row_count", 0)
        if m.get("error"):
            summary[layer]["errors"] += 1
    return summary


def main() -> None:
    gold = Path(_gold_path().replace("*.parquet", ""))
    if not gold.exists() or not list(gold.glob("*.parquet")):
        print(f"No Gold Parquet files found under {gold}")
        print("Run the pipeline first (see docs/LOCAL_RUNBOOK.md).")
        sys.exit(1)

    con = duckdb.connect()

    print("=" * 60)
    print("NexusFlow-X  Gold KPI Report")
    print("=" * 60)

    print(f"\nTotal events (Gold): {total_events(con):,}")

    print("\n--- KPIs by event_type ---")
    print(kpis_by_event_type(con).to_string(index=False))

    print("\n--- Hourly volume ---")
    print(hourly_volume(con).to_string(index=False))

    ms = metrics_summary()
    if ms:
        print("\n--- Pipeline batch metrics ---")
        for layer, stats in ms.items():
            print(
                f"  {layer}: {stats['batches']} batches, "
                f"{stats['rows']:,} rows, {stats['errors']} errors"
            )
    else:
        print("\nNo pipeline metrics file found yet.")

    print()


if __name__ == "__main__":
    main()
