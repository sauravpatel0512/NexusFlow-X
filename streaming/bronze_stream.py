"""Kafka topic nexusflow-events -> Bronze Parquet under NEXUSFLOW_DATA_ROOT (default /app/data in Docker)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from ingestion.data_quality import (
    detect_duplicates,
    load_quality_rules,
    quality_report,
    quarantine_bad_records,
    validate_ranges,
    validate_schema,
)
from ingestion.metrics_line import append_pipeline_metric
from ingestion.paths import data_root, quality_rules_path
from ingestion.schemas import bronze_validate_fields
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

logger = logging.getLogger(__name__)

EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("source", StringType(), True),
        StructField("status", StringType(), True),
        StructField(
            "metrics",
            StructType(
                [
                    StructField("distance", DoubleType(), True),
                    StructField("temperature", DoubleType(), True),
                    StructField("amount", DoubleType(), True),
                    StructField("duration", IntegerType(), True),
                ]
            ),
            True,
        ),
        StructField(
            "extra",
            StructType([StructField("note", StringType(), True)]),
            True,
        ),
    ]
)

spark = SparkSession.builder.appName("NexusFlow-Bronze-Stream").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

IN_DOCKER = Path("/.dockerenv").exists()
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092" if IN_DOCKER else "127.0.0.1:29092",
)
KAFKA_TOPIC_EVENTS = "nexusflow-events"

rules = load_quality_rules(str(quality_rules_path()))
root = data_root()
quarantine_path = str(root / "quarantine" / "bronze")
bronze_path = str(root / "bronze")
# Structured Streaming checkpoint (offsets + progress). Move/delete only when you want a new query run identity or replay strategy.
checkpoint_path = str(root / "checkpoints" / "bronze")

expected_fields = bronze_validate_fields()

df_raw = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
    .option("subscribe", KAFKA_TOPIC_EVENTS)
    .option("startingOffsets", "latest")
    .load()
)

df_parsed = (
    df_raw.selectExpr("CAST(value AS STRING) as json_str")
    .select(from_json(col("json_str"), EVENT_SCHEMA).alias("data"))
    .select("data.*")
)


def _with_flat_metrics(batch_df):
    out = batch_df
    for name in ("distance", "temperature", "amount", "duration"):
        out = out.withColumn(name, col(f"metrics.{name}"))
    return out


def process_batch(batch_df, batch_id):
    if not batch_df.take(1):
        return
    try:
        n = batch_df.count()
        validate_schema(batch_df, expected_fields)
        flat = _with_flat_metrics(batch_df)
        quarantine_bad_records(flat, rules, quarantine_path)
        validate_ranges(flat, rules)
        detect_duplicates(flat, id_field="event_id")
        quality_report(flat, rules)
        batch_df.write.mode("append").parquet(bronze_path)
        append_pipeline_metric("bronze", batch_id, n)
    except Exception as ex:
        logger.exception("Bronze micro-batch %s failed", batch_id)
        try:
            append_pipeline_metric("bronze", batch_id, 0, error=str(ex))
        except Exception:
            pass


logger.info(
    "Bronze stream starting: kafka=%s topic=%s checkpoint=%s parquet_out=%s",
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_EVENTS,
    checkpoint_path,
    bronze_path,
)

query = (
    df_parsed.writeStream.foreachBatch(process_batch)
    .option("checkpointLocation", checkpoint_path)
    .start()
)
query.awaitTermination()
