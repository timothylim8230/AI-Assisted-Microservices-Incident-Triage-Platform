from flask import Flask, jsonify
import requests
import logging
import time

from prometheus_client import Counter, Histogram, Gauge, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

SERVICE_B_URL = "http://service-b:5001/ping"
SERVICE_B_HEALTH_URL = "http://service-b:5001/health"

# Prometheus metrics
REQUEST_COUNT = Counter(
    "service_a_http_requests_total",
    "Total HTTP requests to service-a",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "service_a_http_request_duration_seconds",
    "HTTP request latency for service-a",
    ["endpoint"]
)

DEPENDENCY_HEALTH = Gauge(
    "service_a_dependency_service_b_healthy",
    "Whether service-b is healthy from service-a perspective"
)

@app.route("/")
def home():
    start = time.time()
    try:
        response = requests.get(SERVICE_B_URL, timeout=2)
        response.raise_for_status()
        service_b_data = response.json()

        REQUEST_COUNT.labels(method="GET", endpoint="/", status="200").inc()
        REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)

        return jsonify({
            "message": "hello from service-a",
            "service_b_response": service_b_data
        })
    except Exception as e:
        app.logger.error(f"Failed to reach service-b: {str(e)}")

        REQUEST_COUNT.labels(method="GET", endpoint="/", status="500").inc()
        REQUEST_LATENCY.labels(endpoint="/").observe(time.time() - start)

        return jsonify({
            "message": "hello from service-a",
            "error": f"failed to reach service-b: {str(e)}"
        }), 500

@app.route("/health")
def health():
    start = time.time()
    try:
        response = requests.get(SERVICE_B_HEALTH_URL, timeout=2)
        if response.status_code == 200:
            DEPENDENCY_HEALTH.set(1)
            REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
            REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start)
            return jsonify({"status": "healthy"}), 200

        DEPENDENCY_HEALTH.set(0)
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="500").inc()
        REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start)
        return jsonify({"status": "degraded", "dependency": "service-b unhealthy"}), 500

    except Exception as e:
        app.logger.error(f"Health check failed because service-b is unreachable: {str(e)}")
        DEPENDENCY_HEALTH.set(0)
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="500").inc()
        REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start)
        return jsonify({
            "status": "unhealthy",
            "dependency": "service-b unreachable"
        }), 500

# Expose /metrics using official Prometheus client WSGI app
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/metrics": make_wsgi_app()
})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)