# frontend/app_flask.py
# Flask front-end for the Metasyn FastAPI wrapper (main.py).
# The browser only talks to Flask; Flask forwards requests to FastAPI.
# This avoids CORS issues and keeps the API address in one place.

import os

import requests
from flask import Flask, render_template, request, jsonify

API_URL = "http://127.0.0.1:8000"   # where `uvicorn main:app` is running
TIMEOUT = 300                        # seconds; fitting large files can take a while

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_BYTES", 100 * 1024 * 1024))


def forward(response):
    """Turn a FastAPI response into a Flask response with a consistent error shape."""
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.ok:
        return jsonify(payload)

    detail = payload.get("detail", "Unknown error") if isinstance(payload, dict) else payload
    return jsonify({"error": str(detail)}), response.status_code


def api_unreachable():
    return jsonify({"error": f"Cannot reach the Metasyn API at {API_URL}. "
                             "Start it with: uvicorn main:app --reload"}), 503


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_welcome_message", methods=["GET"])
def get_welcome_message():
    """Used by the page to show whether the API is running."""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
    except requests.exceptions.RequestException:
        return api_unreachable()
    return forward(response)


@app.route("/api/fit-model", methods=["POST"])
def fit_model():
    uploaded = request.files.get("file")
    if uploaded is None or uploaded.filename == "":
        return jsonify({"error": "No file selected."}), 400
    try:
        response = requests.post(
            f"{API_URL}/fit-model/",
            files={"file": (uploaded.filename, uploaded.stream, uploaded.mimetype)},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return api_unreachable()
    return forward(response)


@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    body = request.get_json(silent=True)
    if not body or "model_json" not in body:
        return jsonify({"error": "Request must include model_json."}), 400
    try:
        response = requests.post(f"{API_URL}/synthesize/", json=body, timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        return api_unreachable()
    return forward(response)


if __name__ == "__main__":
    app.run(debug=True)