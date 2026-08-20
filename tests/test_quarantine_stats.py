"""Quarantine breakdown + parse_failures aggregation (no Spark/Kafka)."""
from __future__ import annotations

from pathlib import Path

from ingestion.quarantine_stats import (
    quarantine_breakdown,
    sum_parse_failures,
)


def test_quarantine_breakdown_empty(tmp_path: Path):
    assert quarantine_breakdown(tmp_path) == {
        "bronze": {"files": 0},
        "bronze_parse": {"files": 0},
        "silver": {"files": 0},
    }


def test_quarantine_breakdown_by_layer(tmp_path: Path):
    q = tmp_path / "quarantine"
    (q / "bronze").mkdir(parents=True)
    (q / "bronze_parse").mkdir(parents=True)
    (q / "silver").mkdir(parents=True)
    (q / "bronze" / "a.parquet").write_bytes(b"x")
    (q / "bronze" / "b.parquet").write_bytes(b"x")
    (q / "bronze_parse" / "p.parquet").write_bytes(b"x")
    # nested under silver
    nested = q / "silver" / "part-000"
    nested.mkdir()
    (nested / "c.parquet").write_bytes(b"x")

    got = quarantine_breakdown(tmp_path)
    assert got["bronze"]["files"] == 2
    assert got["bronze_parse"]["files"] == 1
    assert got["silver"]["files"] == 1


def test_quarantine_breakdown_includes_unknown_layer(tmp_path: Path):
    q = tmp_path / "quarantine" / "custom"
    q.mkdir(parents=True)
    (q / "z.parquet").write_bytes(b"x")
    got = quarantine_breakdown(tmp_path)
    assert got["custom"]["files"] == 1
    assert got["bronze"]["files"] == 0


def test_sum_parse_failures_empty():
    assert sum_parse_failures(None) == 0
    assert sum_parse_failures([]) == 0


def test_sum_parse_failures_from_extra():
    lines = [
        {"layer": "bronze", "extra": {"parse_failures": 3}},
        {"layer": "bronze", "extra": {"parse_failures": 2}},
        {"layer": "silver", "row_count": 10},
        {"layer": "bronze", "extra": {"parse_failures": "1"}},
        {"layer": "bronze", "extra": {"parse_failures": "bad"}},
    ]
    assert sum_parse_failures(lines) == 6
