# Failure notes — bugs that actually happened

Short post-mortems from building NexusFlow-X on Windows + Docker. Useful for demos when someone asks “what broke?”

## 1. Kafka connector jar did not match Spark

**Symptom:** Bronze `spark-submit` failed while resolving or loading `spark-sql-kafka-0-10_*` after the Spark image was on **4.1.x**.

**Cause:** `--packages` still requested connector **4.0.1**. Spark’s Kafka source must track the **same major.minor** as the runtime (here Scala **2.13** + Spark **4.1.2**).

**Fix:** Pin

```text
org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.2
```

in [`scripts/spark_submit_bronze.sh`](../scripts/spark_submit_bronze.sh) and document the pair in the runbook. Also set `HOME=/tmp` / `JAVA_TOOL_OPTIONS=-Duser.home=/tmp` so Ivy can download packages inside the container.

**Takeaway:** Treat connector coordinates as part of the image contract, not a one-time copy-paste from an old tutorial.

## 2. Windows CRLF broke `set -o pipefail` in the container

**Symptom:**

```text
bash: set: pipefail: invalid option name
```

when running `bash scripts/spark_submit_*.sh` via `docker exec` into Linux.

**Cause:** Scripts saved with **CRLF**. Bash saw `pipefail\r` as the option name.

**Fix:**

- Repo policy: [`.gitattributes`](../.gitattributes) → `*.sh text eol=lf`
- One-shot repair: `sed -i 's/\r$//' scripts/*.sh` (from WSL/Git Bash)

**Takeaway:** Cross-OS shells fail in ways that look like “bash is broken.” Check line endings before rewriting scripts.

## 3. Spark 4 rejected spaced duration strings

**Symptom:** Gold job aborted with `Failed to parse time string` on `maxFileAge` (and similarly fragile `processingTime` values).

**Cause:** Spark 4’s duration parser expects compact tokens (`600s`, `10min`, `5 minutes` is OK for some triggers but `"10 min"` with an internal space in the wrong option form is not). An earlier draft used `"10 min"`.

**Fix:** Use `"600s"` for `maxFileAge` in [`streaming/gold_aggregations.py`](../streaming/gold_aggregations.py). For demos, override the Gold trigger with `GOLD_PROCESSING_TIME="1 minute"` / `make gold-fast` instead of editing source.

**Takeaway:** Read the error as a **contract** with the version you run—not “Spark is flaky.”

## Related docs

- Operator recovery: [RECOVERY.md](RECOVERY.md)
- Recorded green run: [validation-log.md](validation-log.md)
- Day-to-day commands: [LOCAL_RUNBOOK.md](LOCAL_RUNBOOK.md)
