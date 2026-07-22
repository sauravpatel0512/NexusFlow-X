"""Silver Parquet -> hourly Gold aggregates (tumbling 1h windows) under NEXUSFLOW_DATA_ROOT."""
from __future__ import annotations

import logging
import os

from ingestion.metrics_line import append_pipeline_metric
from ingestion.paths import data_root
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    count,
    current_timestamp,
    hour,
    max,
    min,
    to_date,
    to_timestamp,
    window,
)
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

logger = logging.getLogger(__name__)

silver_schema = StructType(
    [
        StructField("event_id", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("source", StringType(), True),
        StructField("status", StringType(), True),
        StructField("distance", DoubleType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("amount", DoubleType(), True),
        StructField("duration", IntegerType(), True),
        StructField("note", StringType(), True),
    ]
)

spark = (
    SparkSession.builder.appName("NexusFlow-Gold-Hourly-Aggregations")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

root = data_root()
SILVER_INPUT_PATH = str(root / "silver")
GOLD_OUTPUT_PATH = str(root / "gold" / "fact_events_hourly")
CHECKPOINT_PATH = str(root / "checkpoints" / "gold_hourly")

logger.info("Reading Silver from %s", SILVER_INPUT_PATH)
logger.info("Gold output %s", GOLD_OUTPUT_PATH)

df_silver = (
    spark.readStream.format("parquet")
    .schema(silver_schema)
    .option("maxFileAge", "600s")
    .load(SILVER_INPUT_PATH)
)

df_silver = df_silver.withColumn("event_ts", to_timestamp(col("timestamp")))

df_hourly = (
    df_silver.filter(col("event_ts").isNotNull())
    .groupBy(
        window(col("event_ts"), "1 hour"),
        col("event_type"),
        col("source"),
        col("status"),
    )
    .agg(
        count(col("event_id")).alias("event_count"),
        avg(col("distance")).alias("avg_distance"),
        avg(col("temperature")).alias("avg_temperature"),
        avg(col("amount")).alias("avg_amount"),
        avg(col("duration")).alias("avg_duration"),
        min(col("distance")).alias("min_distance"),
        min(col("temperature")).alias("min_temperature"),
        min(col("amount")).alias("min_amount"),
        min(col("duration")).alias("min_duration"),
        max(col("distance")).alias("max_distance"),
        max(col("temperature")).alias("max_temperature"),
        max(col("amount")).alias("max_amount"),
        max(col("duration")).alias("max_duration"),
    )
    .withColumn("date_hour", to_date(col("window.start")))
    .withColumn("hour", hour(col("window.start")))
    .withColumn("created_at", current_timestamp())
    .drop("window")
    .select(
        col("date_hour"),
        col("hour"),
        col("event_type"),
        col("source"),
        col("status"),
        col("event_count"),
        col("avg_distance"),
        col("avg_temperature"),
        col("avg_amount"),
        col("avg_duration"),
        col("min_distance"),
        col("max_distance"),
        col("min_temperature"),
        col("max_temperature"),
        col("min_amount"),
        col("max_amount"),
        col("min_duration"),
        col("max_duration"),
        col("created_at"),
    )
)


def write_gold_batch(batch_df, batch_id):
    try:
        n = batch_df.count()
        logger.info("Gold micro-batch %s: %s aggregation rows", batch_id, n)
        if n == 0:
            append_pipeline_metric("gold", batch_id, 0, extra={"note": "empty_batch"})
            return
        (
            batch_df.write.mode("append")
            .format("parquet")
            .option("mergeSchema", "true")
            .save(GOLD_OUTPUT_PATH)
        )
        append_pipeline_metric("gold", batch_id, n)
    except Exception as ex:
        logger.exception("Gold micro-batch %s failed", batch_id)
        try:
            append_pipeline_metric("gold", batch_id, 0, error=str(ex))
        except Exception:
            pass


# Default 5 minutes. For faster demos: GOLD_PROCESSING_TIME="1 minute"
_gold_trigger = os.getenv("GOLD_PROCESSING_TIME", "5 minutes").strip() or "5 minutes"
logger.info("Gold processingTime trigger: %s", _gold_trigger)

query_hourly = (
    df_hourly.writeStream.outputMode("update")
    .trigger(processingTime=_gold_trigger)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .foreachBatch(write_gold_batch)
    .start()
)

try:
    query_hourly.awaitTermination()
finally:
    spark.stop()
    logger.info("Spark stopped")
