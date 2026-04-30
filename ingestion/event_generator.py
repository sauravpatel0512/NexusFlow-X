"""
Generates synthetic events for the platform.
"""

# Basic event creation function for NexusFlow-X
import uuid
import random
from datetime import datetime, timedelta, timezone


def generate_event(event_type=None):
	"""
	Generates a single synthetic event record.
	Fields are randomized for realism.
	"""
	event_types = ["trip_start", "trip_end", "delivery_update", "sensor_alert", "user_action", "transaction"]
	etype = event_type if event_type else random.choice(event_types)
	now = datetime.now(timezone.utc)
	random_minutes = random.randint(0, 1440)
	event_time = now - timedelta(minutes=random_minutes)
	ts = event_time.astimezone(timezone.utc).isoformat(timespec="milliseconds")
	if ts.endswith("+00:00"):
		ts = ts[:-6] + "Z"
	event = {
		"event_id": str(uuid.uuid4()),
		"timestamp": ts,
		"event_type": etype,
		"source": f"device_{random.randint(1,100)}",
		"status": random.choice(["active", "completed", "error", "pending"]),
		"metrics": {
			"distance": round(random.uniform(0, 100), 2),
			"temperature": round(random.uniform(-10, 40), 1),
			"amount": round(random.uniform(0, 500), 2),
			"duration": random.randint(0, 3600)
		},
		"extra": {
			"note": random.choice(["Initial event", "Outlier", "Corrupt", "Normal"])
		}
	}
	return event

def generate_events_batch(num_events=10):
	"""
	Generates a batch of synthetic events.
	Returns a list of event dicts.
	"""
	return [generate_event() for _ in range(num_events)]

if __name__ == "__main__":
	sample_events = generate_events_batch(5)
	for idx, event in enumerate(sample_events, 1):
		print(f"Event {idx}: {event}\n")