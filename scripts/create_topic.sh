#!/usr/bin/env bash
# Create nexusflow-events and nexusflow-events-dlq if missing (idempotent).
# Run after `docker compose up -d`.
set -euo pipefail

TOPIC="${KAFKA_TOPIC:-nexusflow-events}"
DLQ_TOPIC="${KAFKA_DLQ_TOPIC:-nexusflow-events-dlq}"
BOOTSTRAP="${KAFKA_BOOTSTRAP_INTERNAL:-localhost:9092}"
PARTITIONS="${KAFKA_TOPIC_PARTITIONS:-3}"

ensure_topic() {
  local name="$1"
  if docker exec kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP}" \
    --list 2>/dev/null | grep -qx "${name}"; then
    echo "Topic '${name}' already exists."
    return 0
  fi
  docker exec kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP}" \
    --create \
    --topic "${name}" \
    --partitions "${PARTITIONS}" \
    --replication-factor 1
  echo "Created topic '${name}' (${PARTITIONS} partitions)."
}

echo "Ensuring Kafka topics exist (bootstrap ${BOOTSTRAP})..."

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

ensure_topic "${TOPIC}"
ensure_topic "${DLQ_TOPIC}"
