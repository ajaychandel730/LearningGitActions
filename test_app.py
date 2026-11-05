"""
Comprehensive pytest test suite for the Flask application.
Covers unit tests, route integration tests, error handling,
and mocking external network calls with requests.
"""

from unittest.mock import patch
import pytest
import requests
from app import ITEMS, app, calculate, fetch_github_user


@pytest.fixture
def client():
    """Create a configured Flask test client and reset state."""
    app.config["TESTING"] = True
    ITEMS.clear()
    with app.test_client() as test_client:
        yield test_client


# =====================================================================
# 1. Unit Tests for pure functions
# =====================================================================
@pytest.mark.parametrize(
    "a, b, operation, expected",
    [
        (10, 5, "add", 15),
        (-2, 3, "add", 1),
        (10, 4, "subtract", 6),
        (3, 7, "multiply", 21),
        (20, 4, "divide", 5.0),
        (7, 2, "divide", 3.5),
    ],
)
def test_calculate_success(a, b, operation, expected):
    """Test standard arithmetic operations."""
    assert calculate(a, b, operation) == expected


def test_calculate_divide_by_zero():
    """Test that dividing by zero raises ZeroDivisionError."""
    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero."):
        calculate(10, 0, "divide")


def test_calculate_invalid_operation():
    """Test that unsupported operation raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported operation"):
        calculate(5, 5, "exponent")


# =====================================================================
# 2. Flask Route Integration Tests
# =====================================================================
def test_home_route(client):
    """Test GET / index route."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "online"
    assert "Welcome" in data["message"]


def test_health_route(client):
    """Test GET /health status check."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_api_calculate_endpoint_success(client):
    """Test POST /api/calculate with valid parameters."""
    payload = {"a": 25, "b": 5, "operation": "divide"}
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"] == 5.0
    assert data["operation"] == "divide"


def test_api_calculate_endpoint_missing_fields(client):
    """Test POST /api/calculate with incomplete data."""
    response = client.post("/api/calculate", json={"a": 10})
    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["error"]


def test_api_calculate_endpoint_non_numeric(client):
    """Test POST /api/calculate with non-numeric inputs."""
    payload = {"a": "ten", "b": 2, "operation": "add"}
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 400
    assert "must be numeric" in response.get_json()["error"]


def test_api_calculate_endpoint_zero_division(client):
    """Test POST /api/calculate divide by zero handling."""
    payload = {"a": 10, "b": 0, "operation": "divide"}
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 400
    assert "Cannot divide by zero" in response.get_json()["error"]


def test_api_calculate_endpoint_invalid_operation(client):
    """Test POST /api/calculate with an unsupported operation."""
    payload = {"a": 10, "b": 2, "operation": "modulus"}
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 400
    assert "Unsupported operation" in response.get_json()["error"]


def test_api_calculate_endpoint_no_json(client):
    """Test POST /api/calculate with empty body."""
    response = client.post("/api/calculate", data="plain text")
    assert response.status_code == 400
    assert "Invalid or missing JSON" in response.get_json()["error"]


# =====================================================================
# 3. In-memory Items CRUD Tests
# =====================================================================
def test_items_workflow(client):
    """Test creating items and retrieving the list."""
    # 1. Initial list should be empty
    get_res = client.get("/api/items")
    assert get_res.status_code == 200
    assert get_res.get_json() == {"items": [], "count": 0}

    # 2. Add a new item
    post_res = client.post("/api/items", json={"name": "Setup CI/CD"})
    assert post_res.status_code == 201
    created_item = post_res.get_json()
    assert created_item["id"] == 1
    assert created_item["name"] == "Setup CI/CD"

    # 3. Retrieve items again
    get_res2 = client.get("/api/items")
    assert get_res2.status_code == 200
    assert get_res2.get_json()["count"] == 1

    # 4. Fail when name is missing
    bad_post = client.post("/api/items", json={})
    assert bad_post.status_code == 400
    assert "'name' is required" in bad_post.get_json()["error"]


# =====================================================================
# 4. Error Handler (404) Test
# =====================================================================
def test_404_not_found(client):
    """Test custom 404 response for nonexistent routes."""
    response = client.get("/api/nonexistent-route")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Resource not found"}


# =====================================================================
# 5. External API & Requests Mocking Tests
# =====================================================================
@patch("app.requests.get")
def test_fetch_github_user_success(mock_get, client):
    """Test mock successful external API response via requests."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "login": "octocat",
        "name": "The Octocat",
        "public_repos": 8,
    }

    response = client.get("/api/user/octocat")
    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "octocat"
    assert data["public_repos"] == 8


@patch("app.requests.get")
def test_fetch_github_user_not_found(mock_get, client):
    """Test mock 404 external API response via requests."""
    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {}

    response = client.get("/api/user/nonexistent_user_12345")
    assert response.status_code == 404
    assert "User not found" in response.get_json()["error"]


@patch("app.requests.get")
def test_fetch_github_user_timeout_or_error(mock_get, client):
    """Test mock network exception when requests.get fails."""
    mock_get.side_effect = requests.RequestException("Connection timed out")

    response = client.get("/api/user/anyuser")
    assert response.status_code == 503
    assert "Failed to connect" in response.get_json()["error"]
