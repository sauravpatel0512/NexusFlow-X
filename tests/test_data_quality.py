import os

from ingestion.data_quality import (
    detect_duplicates,
    load_quality_rules,
    quarantine_bad_records,
    validate_ranges,
    validate_schema,
)
from pyspark.sql import Row


def _rules():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return load_quality_rules(os.path.join(root, "ingestion", "quality_rules.yaml"))


def test_validate_schema_ok(spark):
    df = spark.createDataFrame(
        [Row(a=1, b=2)],
    )
    assert validate_schema(df, ["a", "b"]) is True


def test_validate_schema_missing(spark):
    df = spark.createDataFrame([Row(a=1)])
    assert validate_schema(df, ["a", "missing"]) is False


def test_validate_ranges_out_of_range(spark):
    rules = _rules()
    df = spark.createDataFrame([Row(distance=-1.0)])
    validate_ranges(df, rules)


def test_detect_duplicates(spark):
    df = spark.createDataFrame(
        [
            Row(event_id="x"),
            Row(event_id="x"),
            Row(event_id="y"),
        ]
    )
    assert detect_duplicates(df, "event_id") == 1


def test_quarantine_bad_records_writes_parquet(spark, tmp_path):
    rules = _rules()
    out = tmp_path / "q"
    df = spark.createDataFrame([Row(distance=-5.0, event_id="e1")])
    quarantine_bad_records(df, rules, str(out))
    assert out.exists()
    assert list(out.glob("*.parquet")) or list(out.rglob("*.parquet"))
