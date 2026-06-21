"""Bronze Parquet -> flattened Silver Parquet under NEXUSFLOW_DATA_ROOT."""
from __future__ import annotations

import logging

from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

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
from ingestion.schemas import silver_validate_fields

logger = logging.getLogger(__name__)

bronze_schema = StructType(
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

spark = SparkSession.builder.appName("NexusFlow-Silver-Stream").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

root = data_root()
bronze_in = str(root / "bronze")
silver_out = str(root / "silver")
# Same checkpoint semantics as Bronze: holds streaming offsets for this query id.
checkpoint_path = str(root / "checkpoints" / "silver")
quarantine_path = str(root / "quarantine" / "silver")

rules = load_quality_rules(str(quality_rules_path()))

expected_fields = silver_validate_fields()


def flatten_and_clean(df):
    df_flat = (
        df.withColumn("distance", col("metrics.distance"))
        .withColumn("temperature", col("metrics.temperature"))
        .withColumn("amount", col("metrics.amount"))
        .withColumn("duration", col("metrics.duration"))
        .withColumn("note", col("extra.note"))
        .drop("metrics", "extra")
    )
    return df_flat.fillna(
        {
            "distance": 0.0,
            "temperature": 0.0,
            "amount": 0.0,
            "duration": 0,
            "note": "",
        }
    )


def process_batch(batch_df, batch_id):
    if not batch_df.take(1):
        return
    try:
        out = flatten_and_clean(batch_df)
        n = out.count()
        validate_schema(out, expected_fields)
        quarantine_bad_records(out, rules, quarantine_path)
        validate_ranges(out, rules)
        detect_duplicates(out, id_field="event_id")
        quality_report(out, rules)
        out.write.mode("append").parquet(silver_out)
        append_pipeline_metric("silver", batch_id, n)
    except Exception as ex:
        logger.exception("Silver micro-batch %s failed", batch_id)
        try:
            append_pipeline_metric("silver", batch_id, 0, error=str(ex))
        except Exception:
            pass


df_bronze = (
    spark.readStream.format("parquet")
    .schema(bronze_schema)
    .load(bronze_in)
)

logger.info(
    "Silver stream starting: bronze_in=%s checkpoint=%s parquet_out=%s",
    bronze_in,
    checkpoint_path,
    silver_out,
)

query = (
    df_bronze.writeStream.foreachBatch(process_batch)
    .option("checkpointLocation", checkpoint_path)
    .start()
)
query.awaitTermination()
