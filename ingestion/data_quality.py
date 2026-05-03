"""
NexusFlow-X Data Quality Framework
----------------------------------
Reusable validation utilities for Bronze, Silver, and Gold layers.
"""
import os
import yaml
import logging
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, countDistinct

# ================================
# Setup Logging
# ================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# Load Quality Rules
# ================================
def load_quality_rules(rules_path="ingestion/quality_rules.yaml"):
    if not os.path.exists(rules_path):
        logger.warning(f"Quality rules file not found: {rules_path}")
        return {}
    with open(rules_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ================================
# Schema Validation
# ================================
def validate_schema(df: DataFrame, expected_fields: list):
    actual_fields = set(df.columns)
    expected = set(expected_fields)
    missing = expected - actual_fields
    extra = actual_fields - expected
    if missing:
        logger.error(
            "Schema validation failed: missing required fields: %s",
            sorted(missing),
        )
    if extra:
        logger.warning(
            "Schema validation: unexpected extra fields: %s",
            sorted(extra),
        )
    return not missing

# ================================
# Numeric Range Validation
# ================================
def validate_ranges(df: DataFrame, rules: dict):
    for field, rule in rules.get("numeric_ranges", {}).items():
        min_val = rule.get("min")
        max_val = rule.get("max")
        if field in df.columns:
            out_of_range = df.filter((col(field) < min_val) | (col(field) > max_val)).count()
            if out_of_range > 0:
                logger.warning(f"{out_of_range} records in '{field}' out of range [{min_val}, {max_val}]")
    return df

# ================================
# Duplicate Detection
# ================================
def detect_duplicates(df: DataFrame, id_field="event_id"):
    total = df.count()
    unique = df.select(countDistinct(id_field)).collect()[0][0]
    dups = total - unique
    if dups > 0:
        logger.warning(f"{dups} duplicate records found on '{id_field}'")
    return dups

# ================================
# Quarantine Bad Records
# ================================
def quarantine_bad_records(df: DataFrame, rules: dict, quarantine_path: str):
    bad = None
    for field, rule in rules.get("numeric_ranges", {}).items():
        min_val = rule.get("min")
        max_val = rule.get("max")
        if field in df.columns:
            out = df.filter((col(field) < min_val) | (col(field) > max_val))
            bad = out if bad is None else bad.union(out)
    if bad is not None:
        n = bad.count()
        if n > 0:
            logger.info("Quarantining %s bad records to %s", n, quarantine_path)
            bad.write.mode("append").parquet(quarantine_path)
    return bad

# ================================
# Quality Report
# ================================
def quality_report(df: DataFrame, rules: dict):
    report = {}
    for field, rule in rules.get("numeric_ranges", {}).items():
        if field in df.columns:
            min_val = rule.get("min")
            max_val = rule.get("max")
            out_of_range = df.filter((col(field) < min_val) | (col(field) > max_val)).count()
            report[field] = {"out_of_range": out_of_range}
    logger.info(f"Quality report: {report}")
    return report
