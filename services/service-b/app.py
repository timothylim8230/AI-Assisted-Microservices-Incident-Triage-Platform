from flask import Flask, jsonify
import logging
import time

from prometheus_client import Counter, Histogram, Gauge, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

service_b_healthy = True

# Prometheus metrics
REQUEST_COUNT = Counter(
    "service_b_http_requests_total",
    "Total HTTP requests to service-b",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "service_b_http_request_duration_seconds",
    "HTTP request latency for service-b",
    ["endpoint"]
)

SERVICE_HEALTH = Gauge(
    "service_b_health_status",
    "Health status of service-b (1=healthy, 0=unhealthy)"
)

@app.route("/ping")
def ping():
    start = time.time()
    global service_b_healthy

    if not service_b_healthy:
        SERVICE_HEALTH.set(0)
        REQUEST_COUNT.labels(method="GET", endpoint="/ping", status="500").inc()
        REQUEST_LATENCY.labels(endpoint="/ping").observe(time.time() - start)
        return jsonify({"message": "service-b is failing"}), 500

    SERVICE_HEALTH.set(1)
    REQUEST_COUNT.labels(method="GET", endpoint="/ping", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/ping").observe(time.time() - start)
    return jsonify({"message": "pong from service-b"})

@app.route("/health")
def health():
    start = time.time()
    global service_b_healthy

    if service_b_healthy:
        SERVICE_HEALTH.set(1)
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
        REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start)
        return jsonify({"status": "healthy"}), 200

    SERVICE_HEALTH.set(0)
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="500").inc()
    REQUEST_LATENCY.labels(endpoint="/health").observe(time.time() - start)
    return jsonify({"status": "unhealthy"}), 500

@app.route("/fail")
def fail():
    global service_b_healthy
    service_b_healthy = False
    SERVICE_HEALTH.set(0)
    return jsonify({"message": "service-b set to unhealthy"})

@app.route("/recover")
def recover():
    global service_b_healthy
    service_b_healthy = True
    SERVICE_HEALTH.set(1)
    return jsonify({"message": "service-b recovered"})

# Expose /metrics using official Prometheus client WSGI app
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/metrics": make_wsgi_app()
})

if __name__ == "__main__":
    SERVICE_HEALTH.set(1)
    app.run(host="0.0.0.0", port=5001)