# NexusFlow-X — operator shortcuts (run from repo root; use WSL/Git Bash on Windows).
# Requires Docker Compose and running containers for exec targets.

.DEFAULT_GOAL := help

.PHONY: help up down bronze silver gold producer test validate query dashboard lint

help:
	@echo "NexusFlow-X targets:"
	@echo "  make up / down       Start or stop Docker Compose (kafka + nexus-spark)"
	@echo "  make bronze|silver|gold   spark-submit streaming jobs in nexus-spark"
	@echo "  make producer        Produce events (ARGS='--batches 30' or ARGS='--once')"
	@echo "  make test            pytest"
	@echo "  make lint            ruff check ."
	@echo "  make validate        Parse quality_rules.yaml"
	@echo "  make query           DuckDB Gold KPI CLI"
	@echo "  make dashboard       Streamlit dashboard (localhost:8501)"

up:
	docker compose up -d

down:
	docker compose down

bronze:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_bronze.sh"

silver:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_silver.sh"

gold:
	docker exec nexus-spark bash -c "cd /app && export PYTHONPATH=/app && bash scripts/spark_submit_gold.sh"

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
