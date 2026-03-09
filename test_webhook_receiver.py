from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/alerts/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("=== ALERT RECEIVED ===")
    print(data)
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)