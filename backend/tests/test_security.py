from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# Test 1: Rate Limiting & Request ID Header
def test_rate_limiting_and_request_id():
    # Attempt to hit the route multiple times to trigger rate limit (5/min)
    responses = []
    for _ in range(6):
        response = client.post("/api/orders/create")
        responses.append(response)

    # First few should be 200, last must be 429
    assert responses[0].status_code == 200
    assert responses[-1].status_code == 429
    assert responses[-1].json() == {"error": "Rate limit exceeded: 5 per 1 minute"}

    # All responses must have the X-Request-Id header injected
    for r in responses:
        assert "x-request-id" in r.headers
        assert len(r.headers["x-request-id"]) > 10

# Test 2: Missing Auth Token -> 401
def test_missing_auth_token_for_admin():
    response = client.get("/api/admin/orders")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

# Test 3: Standard User trying to access Admin Route -> 403
@patch("app.api.deps.auth.verify_id_token")
def test_user_forbidden_admin_route(verify_mock):
    # Mocking verify_id_token to return standard user without admin claims
    verify_mock.return_value = {
        "uid": "regular_user_1",
        "email": "user@gmail.com"
        # "admin" claim is missing
    }
    
    response = client.get("/api/admin/orders", headers={"Authorization": "Bearer fake-token-123"})
    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"

# Test 4: Admin User accessing Admin Route -> 200
@patch("app.api.deps.auth.verify_id_token")
def test_admin_access_allowed(verify_mock):
    # Mocking verify_id_token to return admin claims
    verify_mock.return_value = {
        "uid": "admin_uid_99",
        "email": "admin@emektup.com",
        "admin": True
    }
    
    response = client.get("/api/admin/orders", headers={"Authorization": "Bearer valid-admin-token"})
    assert response.status_code == 200
    assert response.json() == {"message": "Admin orders list"}
