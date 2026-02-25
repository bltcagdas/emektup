import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from mockfirestore import MockFirestore
from app.api.routes.orders import get_db
from app.core.rate_limit import limiter

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_rate_limit():
    # Clear rate limiter memory before each test
    limiter._storage.reset()
    yield

class DummyBatch:
    def __init__(self, db):
        self.db = db
    def set(self, ref, data):
        self.db.collection(ref._path[0]).document(ref.id).set(data)
    def commit(self):
        pass

@pytest.fixture
def mock_db():
    mock = MockFirestore()
    # Inject batch method for testing since mockfirestore lacks it
    mock.batch = lambda: DummyBatch(mock)
    
    app.dependency_overrides[get_db] = lambda: mock
    with patch("app.api.routes.orders.get_db", return_value=mock):
        yield mock
    app.dependency_overrides.clear()

def test_order_creation_and_tracking(mock_db):
    # 1. Create Order Payload
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

    # 2. Fire Create Request
    response = client.post("/api/orders/create", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert "order_id" in data
    assert "tracking_code" in data
    assert data["status"] == "CREATED"
    
    tracking_code = data["tracking_code"]
    
    # Verify rate limit still applies
    for _ in range(5):
        client.post("/api/orders/create", json=payload)
    
    rate_limited = client.post("/api/orders/create", json=payload)
    assert rate_limited.status_code == 429
    
    # 3. Fire Track Request
    track_response = client.get(f"/api/orders/track/{tracking_code}")
    assert track_response.status_code == 200
    
    track_data = track_response.json()
    assert track_data["tracking_code"] == tracking_code
    assert track_data["status"] == "CREATED"
    assert "public_step_label" in track_data
    assert track_data["public_step_label"] == "Sipariş Alındı"
    # Ensure PII is not leaked
    assert "recipient" not in track_data
    assert "letter_content" not in track_data
    assert "notes" not in track_data
    
    # 4. Unknown Track Request
    bad_track = client.get("/api/orders/track/UNKNOWNCODE")
    assert bad_track.status_code == 404

def test_pydantic_sanitization(mock_db):
    # Payload with missing required recipient
    payload = {
        "is_guest": True,
        "letter_content": "Merhaba",
    }
    response = client.post("/api/orders/create", json=payload)
    # Should throw 422 Unprocessable Entity due to Pydantic validating schema
    assert response.status_code == 422
    
    # Payload with exact sanitization limits
    good_payload = {
        "is_guest": True,
        "recipient": {
            "name": "V" * 100, # Max
            "address": "B" * 500 # Max
        },
        "letter_content": "C" * 20000 # Max
    }
    response2 = client.post("/api/orders/create", json=good_payload)
    assert response2.status_code == 201
    
    # Payload exceeding limits
    bad_payload = {
        "is_guest": True,
        "recipient": {
            "name": "V" * 101, # Exceeds 100
            "address": "B" * 500
        },
        "letter_content": "Hello"
    }
    response3 = client.post("/api/orders/create", json=bad_payload)
    assert response3.status_code == 422
