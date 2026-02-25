import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from mockfirestore import MockFirestore
from app.api.routes.admin import get_db
from app.api.deps import UserRecord, require_admin

client = TestClient(app)

# Inject dummy methods for MockFirestore to simulate transactions
class DummyTransaction:
    def __init__(self, db):
        self.db = db
    def update(self, ref, data):
        self.db.collection(ref._path[0]).document(ref.id).update(data)
    def set(self, ref, data):
        self.db.collection(ref._path[0]).document(ref.id).set(data)
    def get(self, ref):
        return ref.get()

# We need to monkeypath the firestore transactional decorator
from firebase_admin import firestore
import mockfirestore.document

def fake_transactional(func):
    def wrapper(transaction, *args, **kwargs):
        return func(transaction, *args, **kwargs)
    return wrapper
firestore.transactional = fake_transactional

original_doc_get = mockfirestore.document.DocumentReference.get
def fake_doc_get(self, *args, **kwargs):
    kwargs.pop("transaction", None)
    return original_doc_get(self, *args, **kwargs)
mockfirestore.document.DocumentReference.get = fake_doc_get

import datetime

@pytest.fixture
def mock_db():
    mock = MockFirestore()
    mock.transaction = lambda: DummyTransaction(mock)
    
    app.dependency_overrides[get_db] = lambda: mock
    
    now = datetime.datetime.now()
    
    # Pre-seed the database with an order for our specs
    mock.collection("orders").document("test_order_1").set({
        "status": "CREATED",
        "tracking_code": "TRACK123",
        "total_amount": 100.0,
        "is_guest": True,
        "recipient": {"address": "Kadikoy, Istanbul"},
        "created_at": now,
        "status_updated_at": now
    })
    mock.collection("order_public").document("TRACK123").set({
        "status": "CREATED",
        "created_at": now,
        "status_updated_at": now
    })
    
    with patch("app.api.routes.admin.get_db", return_value=mock):
        yield mock
    app.dependency_overrides.clear()

# Override the admin auth check for tests
def override_require_admin():
    return UserRecord(uid="admin_123", email="admin@test.com", claims={"admin": True})

def override_not_admin():
    return UserRecord(uid="user_999", email="user@test.com", claims={"admin": False})


def test_admin_list_orders(mock_db):
    app.dependency_overrides[require_admin] = override_require_admin
    
    res = client.get("/api/admin/orders")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["order_id"] == "test_order_1"
    assert data["items"][0]["recipient_summary"] == "Kadikoy, Istanbul" # PII hidden
    
    app.dependency_overrides.clear()

def test_admin_patch_status_success(mock_db):
    app.dependency_overrides[require_admin] = override_require_admin
    
    payload = {
        "to_status": "PAID",
        "expected_from_status": "CREATED",
        "note": "Payment validated manually"
    }
    
    res = client.patch("/api/admin/orders/test_order_1/status", json=payload)
    assert res.status_code == 200
    
    # Verify in DB
    order = mock_db.collection("orders").document("test_order_1").get().to_dict()
    assert order["status"] == "PAID"
    
    app.dependency_overrides.clear()

def test_admin_patch_optimistic_lock_mismatch(mock_db):
    app.dependency_overrides[require_admin] = override_require_admin
    
    payload = {
        "to_status": "PAID",
        "expected_from_status": "READY_FOR_PRINT",  # INCORRECT
    }
    
    res = client.patch("/api/admin/orders/test_order_1/status", json=payload)
    assert res.status_code == 409
    data = res.json()["detail"]
    assert data["code"] == "STATUS_MISMATCH"
    assert data["current_status"] == "CREATED"
    
    app.dependency_overrides.clear()

def test_admin_patch_invalid_transition(mock_db):
    app.dependency_overrides[require_admin] = override_require_admin
    
    # Try to jump directly to SHIPPED from CREATED
    payload = {
        "to_status": "SHIPPED",
        "expected_from_status": "CREATED",
    }
    
    res = client.patch("/api/admin/orders/test_order_1/status", json=payload)
    assert res.status_code == 400
    assert "Invalid transition" in res.json()["detail"]
    
    app.dependency_overrides.clear()
