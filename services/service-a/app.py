from flask import Flask, jsonify
import requests

app = Flask(__name__)

SERVICE_B_URL = "http://service-b:5001/ping"

@app.route("/")
def home():
    try:
        response = requests.get(SERVICE_B_URL, timeout=2)
        service_b_data = response.json()
        return jsonify({
            "message": "hello from service-a",
            "service_b_response": service_b_data
        })
    except Exception as e:
        return jsonify({
            "message": "hello from service-a",
            "error": f"failed to reach service-b: {str(e)}"
        }), 500

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)