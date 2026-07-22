#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export HOME="${HOME:-/tmp}"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
# Must match Spark runtime in the container (spark:python3 → currently 4.1.x)
/opt/spark/bin/spark-submit \
  --master 'local[2]' \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.2 \
  streaming/bronze_stream.py
