from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from mockfirestore import MockFirestore

client = TestClient(app)

# Test 1: Rate Limiting & Request ID Header
@patch("app.api.routes.orders.get_db")
def test_rate_limiting_and_request_id(db_mock):
    class DummyBatch:
        def __init__(self, db):
            self.db = db
        def set(self, ref, data):
            self.db.collection(ref._path[0]).document(ref.id).set(data)
        def commit(self):
            pass

    mock = MockFirestore()
    mock.batch = lambda: DummyBatch(mock)
    db_mock.return_value = mock
    
    # Attempt to hit the route multiple times to trigger rate limit (5/min)
    responses = []
    payload = {
        "is_guest": True,
        "recipient": {
            "name": "Ahmet Yilmaz",
            "address": "Ataturk Cad. No: 1, Istanbul",
            "phone": "05551234567"
        },
        "letter_content": "Merhaba Ahmet, nasilsin?",
        "notes": "Hizli gitsin lutfen"
    }
    for _ in range(6):
        response = client.post("/api/orders/create", json=payload)
        responses.append(response)

    # First few should be 201, last must be 429
    assert responses[0].status_code == 201
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
@patch("app.api.routes.admin.get_db")
@patch("app.api.deps.auth.verify_id_token")
def test_admin_access_allowed(verify_mock, db_mock):
    # Mocking verify_id_token to return admin claims
    verify_mock.return_value = {
        "uid": "admin_uid_99",
        "email": "admin@emektup.com",
        "admin": True
    }
    
    db_mock.return_value = MockFirestore()
    
    response = client.get("/api/admin/orders", headers={"Authorization": "Bearer valid-admin-token"})
    assert response.status_code == 200
