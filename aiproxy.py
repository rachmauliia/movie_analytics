import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(_name_)

# Allow requests only from the HTML file opened locally in a browser
CORS(app, origins=["null", "http://localhost:8501", "http://127.0.0.1:8501",
                   "http://localhost:5500", "http://127.0.0.1:5500"])

# ── Put your Anthropic API key here, OR use an environment variable ──────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "sk-ant-api03-PASTE_YOUR_KEY_HERE")
# ─────────────────────────────────────────────────────────────────────────────

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

@app.route("/chat", methods=["POST"])
def chat():
    """Forward the request body to Anthropic and return the response."""
    if not ANTHROPIC_API_KEY or "PASTE_YOUR_KEY_HERE" in ANTHROPIC_API_KEY:
        return jsonify({"error": {"message": "API key not set in ai_proxy.py"}}), 500

    try:
        body = request.get_json(force=True)
        resp = requests.post(
            ANTHROPIC_URL,
            json=body,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            timeout=60,
        )
        return jsonify(resp.json()), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({"error": {"message": "Request to Anthropic timed out."}}), 504
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500


@app.route("/health", methods=["GET"])
def health():
    """Simple health check — open http://localhost:5001/health in browser to verify proxy is running."""
    key_set = bool(ANTHROPIC_API_KEY) and "PASTE_YOUR_KEY_HERE" not in ANTHROPIC_API_KEY
    return jsonify({"status": "ok", "api_key_set": key_set})


if _name_ == "_main_":
    print("=" * 55)
    print("  DVDRental AI Proxy running at http://localhost:5001")
    print("  Health check: http://localhost:5001/health")
    print("=" * 55)
    key_ok = ANTHROPIC_API_KEY and "PASTE_YOUR_KEY_HERE" not in ANTHROPIC_API_KEY
    if not key_ok:
        print("\n  WARNING: API key not set!")
        print("  Edit ai_proxy.py and replace PASTE_YOUR_KEY_HERE")
        print("  OR run:  set ANTHROPIC_API_KEY=sk-ant-api03-...\n")
    else:
        print("\n  API key loaded. Proxy is ready.\n")
    app.run(host="127.0.0.1", port=5001, debug=False)