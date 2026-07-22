#!/usr/bin/env bash
# Create nexusflow-events if missing (idempotent). Run after `docker compose up -d`.
set -euo pipefail

TOPIC="${KAFKA_TOPIC:-nexusflow-events}"
BOOTSTRAP="${KAFKA_BOOTSTRAP_INTERNAL:-localhost:9092}"
PARTITIONS="${KAFKA_TOPIC_PARTITIONS:-3}"

echo "Ensuring Kafka topic '${TOPIC}' exists (bootstrap ${BOOTSTRAP})..."

# Wait for Kafka broker to accept connections (up to ~60s).
for i in $(seq 1 30); do
  if docker exec kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP}" \
    --list >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Kafka not ready after waiting." >&2
    exit 1
  fi
  sleep 2
done

if docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP}" \
  --list 2>/dev/null | grep -qx "${TOPIC}"; then
  echo "Topic '${TOPIC}' already exists."
  exit 0
fi

docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP}" \
  --create \
  --topic "${TOPIC}" \
  --partitions "${PARTITIONS}" \
  --replication-factor 1

echo "Created topic '${TOPIC}' (${PARTITIONS} partitions)."
