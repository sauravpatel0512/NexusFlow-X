# NexusFlow-X — operator shortcuts (run from repo root; use WSL/Git Bash on Windows).
# Requires Docker Compose and running containers for exec targets.

.DEFAULT_GOAL := help

.PHONY: help up down topic bronze silver gold producer test validate query dashboard lint

help:
	@echo "NexusFlow-X targets:"
	@echo "  make up / down       Start or stop Docker Compose (kafka + nexus-spark)"
	@echo "  make topic           Ensure Kafka topic nexusflow-events exists"
	@echo "  make bronze|silver|gold   spark-submit streaming jobs in nexus-spark"
	@echo "  make gold-fast       Gold with GOLD_PROCESSING_TIME='1 minute' (demo)"
	@echo "  make producer        Produce events (ARGS='--batches 30' or ARGS='--once')"
	@echo "  make test            pytest"
	@echo "  make lint            ruff check ."
	@echo "  make validate        Parse quality_rules.yaml"
	@echo "  make query           DuckDB Gold KPI CLI"
	@echo "  make dashboard       Streamlit dashboard (localhost:8501)"

up:
	docker compose up -d
	@$(MAKE) topic

down:
	docker compose down

topic:
	bash scripts/create_topic.sh

bronze:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_bronze.sh"

silver:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_silver.sh"

gold:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_gold.sh"

# Faster demo path — wait ~1 minute instead of 5 for first Gold micro-batch.
gold-fast:
	docker exec -e GOLD_PROCESSING_TIME="1 minute" nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_gold.sh"

# Optional: make producer ARGS='--batches 30'  or  ARGS='--once'
producer:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && python3 -m ingestion.producer $(ARGS)"

test:
	python -m pytest tests/ -q

lint:
	python -m ruff check .

validate:
	python -c "import yaml; yaml.safe_load(open('ingestion/quality_rules.yaml')); print('quality_rules.yaml OK')"

query:
	python analytics/gold_query.py

dashboard:
	python -m streamlit run analytics/dashboard.py
