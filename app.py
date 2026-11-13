"""
Flask application demonstrating routes, calculations, in-memory state,
and external API requests for CI/CD and testing.
"""

from typing import Any, Dict, Optional, Tuple
from flask import Flask, jsonify, request
from flask_wtf.csrf import CSRFProtect
import requests
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY")
csrf = CSRFProtect()
csrf.init_app(app)

# In-memory storage for items demo
ITEMS: list[Dict[str, Any]] = []


def calculate(a: float, b: float, operation: str) -> float:
    """Perform basic arithmetic calculations."""
    if operation == "add":
        return a + b
    if operation == "subtract":
        return a - b
    if operation == "multiply":
        return a * b
    if operation == "divide":
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return a / b
    raise ValueError(f"Unsupported operation: {operation}")


def fetch_github_user(username: str, timeout: int = 5) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Fetch public GitHub user profile using requests.
    Returns (data, status_code).
    """
    url = f"https://api.github.com/users/{username}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return {
                "username": data.get("login"),
                "name": data.get("name"),
                "public_repos": data.get("public_repos", 0),
            }, 200
        return {"error": "User not found or upstream error"}, response.status_code
    except requests.RequestException:
        return {"error": "Failed to connect to external service"}, 503


@app.route("/", methods=["GET"])
def home():
    """Index route."""
    return jsonify({
        "message": "Welcome to Flask CI/CD API",
        "status": "online"
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """
    Perform arithmetic via POST request.
    Expected JSON: {"a": 10, "b": 2, "operation": "divide"}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    if "a" not in data or "b" not in data or "operation" not in data:
        return jsonify({"error": "Missing required fields: 'a', 'b', 'operation'"}), 400

    try:
        a = float(data["a"])
        b = float(data["b"])
    except (ValueError, TypeError):
        return jsonify({"error": "Fields 'a' and 'b' must be numeric"}), 400

    operation = str(data["operation"]).lower()

    try:
        result = calculate(a, b, operation)
        return jsonify({
            "a": a,
            "b": b,
            "operation": operation,
            "result": result
        }), 200
    except ZeroDivisionError as err:
        return jsonify({"error": str(err)}), 400
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.route("/api/items", methods=["GET", "POST"])
def manage_items():
    """List or create items."""
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data or "name" not in data:
            return jsonify({"error": "'name' is required"}), 400

        item = {
            "id": len(ITEMS) + 1,
            "name": str(data["name"]).strip()
        }
        ITEMS.append(item)
        return jsonify(item), 201

    return jsonify({"items": ITEMS, "count": len(ITEMS)}), 200


@app.route("/api/user/<username>", methods=["GET"])
def get_user_profile(username: str):
    """Fetch external user profile."""
    result, status_code = fetch_github_user(username)
    return jsonify(result), status_code


@app.errorhandler(404)
def not_found(error):
    """Custom 404 JSON error handler."""
    return jsonify({"error": "Resource not found"}), 404


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
