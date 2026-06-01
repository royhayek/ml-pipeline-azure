"""
Locust load test for the Weather ML API.

Simulates a burst of 100 concurrent users hitting the /predict endpoint
to exercise Container Apps autoscaling (0 -> 3 replicas).

Usage:
    pip install locust
    locust -f tests/load_test.py \
           --host https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io \
           --users 100 --spawn-rate 20 --run-time 2m --headless \
           --html docs/load_testing_report.html

Or open the Locust web UI:
    locust -f tests/load_test.py \
           --host https://ca-mlapi.orangesky-cc1a99c3.switzerlandnorth.azurecontainerapps.io
    Then open http://localhost:8089
"""

import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


SAMPLE_RECORDS = [
    {"temperature_c": 22.5, "humidity": 0.65, "wind_speed_kmh": 12.0,
     "wind_bearing_deg": 180, "visibility_km": 9.5, "pressure_mb": 1013.0,
     "is_rain": 0, "hour": 14, "month": 6},
    {"temperature_c": -3.2, "humidity": 0.88, "wind_speed_kmh": 28.0,
     "wind_bearing_deg": 270, "visibility_km": 4.0, "pressure_mb": 998.0,
     "is_rain": 1, "hour": 8, "month": 1},
    {"temperature_c": 34.1, "humidity": 0.32, "wind_speed_kmh": 5.0,
     "wind_bearing_deg": 90, "visibility_km": 14.0, "pressure_mb": 1018.0,
     "is_rain": 0, "hour": 15, "month": 7},
]


def _random_record() -> dict:
    return {
        "temperature_c":    round(random.uniform(-10, 38), 1),
        "humidity":         round(random.uniform(0.2, 0.98), 2),
        "wind_speed_kmh":   round(random.uniform(0, 50), 1),
        "wind_bearing_deg": random.randint(0, 359),
        "visibility_km":    round(random.uniform(0.5, 16), 1),
        "pressure_mb":      round(1010 + random.gauss(0, 10), 1),
        "is_rain":          random.choice([0, 0, 0, 1]),
        "hour":             random.randint(0, 23),
        "month":            random.randint(1, 12),
    }


class MLApiUser(HttpUser):
    """Simulates a single API consumer sending weather batches."""

    wait_time = between(0.05, 0.3)

    def on_start(self):
        resp = self.client.get("/health", name="/health (warmup)")
        if resp.status_code != 200:
            self.environment.runner.quit()

    @task(8)
    def predict_single(self):
        """Single-record prediction - most common case."""
        self.client.post(
            "/predict",
            json={"records": [_random_record()]},
            name="/predict (single)",
        )

    @task(3)
    def predict_batch(self):
        """Batch prediction (5-20 records) - pipeline worker pattern."""
        n = random.randint(5, 20)
        self.client.post(
            "/predict",
            json={"records": [_random_record() for _ in range(n)]},
            name="/predict (batch)",
        )

    @task(2)
    def predict_fixed(self):
        """Fixed sample record - for reproducible latency measurement."""
        self.client.post(
            "/predict",
            json={"records": [random.choice(SAMPLE_RECORDS)]},
            name="/predict (fixed)",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(1)
    def get_metrics(self):
        self.client.get("/metrics", name="/metrics")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    if not isinstance(environment.runner, MasterRunner):
        print(
            "\nLoad test started.\n"
            "Monitor autoscaling in Azure Portal:\n"
            "  Container Apps > ca-mlapi > Metrics > Replica Count\n"
            "Application Insights:\n"
            "  requests | summarize count() by bin(timestamp, 1m) | render timechart\n"
        )
