import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from mockfirestore import MockFirestore
from app.api.routes.payments import get_db
from firebase_admin import firestore
import mockfirestore.document
import datetime

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



@pytest.fixture
def mock_db():
    mock = MockFirestore()
    mock.transaction = lambda: DummyTransaction(mock)
    
    app.dependency_overrides[get_db] = lambda: mock
    
    now = datetime.datetime.now()
    
    # Pre-seed the database with an order for our specs
    mock.collection("orders").document("order_payment_1").set({
        "status": "CREATED",
        "tracking_code": "TRACKPAY123",
        "total_amount": 100.0,
        "currency": "TRY",
        "payment_status": "PENDING"
    })
    mock.collection("order_public").document("TRACKPAY123").set({
        "status": "CREATED",
        "created_at": now,
        "status_updated_at": now
    })
    
    with patch("app.api.routes.payments.get_db", return_value=mock):
        yield mock
    app.dependency_overrides.clear()


def test_create_payment_intent(mock_db):
    payload = {
        "order_id": "order_payment_1"
    }
    
    res = client.post("/api/payments/create-intent", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "checkout_url" in data
    assert data["status"] == "success"
    
    # Verify Payment Doc Created
    payment_doc = mock_db.collection("payments").document(data["token"]).get()
    assert payment_doc.exists
    p_data = payment_doc.to_dict()
    assert p_data["amount"] == 100.0
    assert p_data["status"] == "PENDING"
    assert p_data["order_id"] == "order_payment_1"
    
    # Idempotency / Double click test
    res2 = client.post("/api/payments/create-intent", json=payload)
    assert res2.status_code == 200
    assert res2.json()["token"] == data["token"] # Should reuse the pending token instead of double charging


def test_payment_webhook_missing_signature(mock_db):
    payload = {
        "token": "sandbox_token_order_payment_1",
        "status": "SUCCESS",
        "paymentId": "123",
        "conversationId": "order_payment_1"
    }
    
    res = client.post("/api/payments/webhook", json=payload)
    assert res.status_code == 401
    assert "Missing signature" in res.json()["detail"]


def test_payment_webhook_invalid_signature(mock_db):
    payload = {
        "token": "sandbox_token_order_payment_1",
        "status": "SUCCESS",
        "paymentId": "123",
        "conversationId": "order_payment_1"
    }
    
    res = client.post("/api/payments/webhook", json=payload, headers={"x-iyz-signature": "bad_sig"})
    assert res.status_code == 401
    assert "Invalid webhook signature" in res.json()["detail"]


def test_payment_webhook_success_and_dedup(mock_db):
    # First, mock a payment that is PENDING
    mock_db.collection("payments").document("val_token_12").set({
        "order_id": "order_payment_1",
        "status": "PENDING"
    })
    
    payload = {
        "token": "val_token_12",
        "status": "SUCCESS",
        "paymentId": "iyz_999",
        "conversationId": "order_payment_1"
    }
    
    res = client.post("/api/payments/webhook", json=payload, headers={"x-iyz-signature": "mock_valid_signature"})
    assert res.status_code == 200
    assert res.json()["message"] == "Webhook processed successfully"
    
    # Verify Fan-out status changes
    payment = mock_db.collection("payments").document("val_token_12").get().to_dict()
    assert payment["status"] == "SUCCEEDED"
    
    order = mock_db.collection("orders").document("order_payment_1").get().to_dict()
    assert order["payment_status"] == "PAID"
    assert order["status"] == "PAID"
    
    public_doc = mock_db.collection("order_public").document("TRACKPAY123").get().to_dict()
    assert public_doc["status"] == "PAID"
    assert "Hazırlanıyor" in public_doc["public_step_label"]
    
    # TEST DEDUP (Process again immediately)
    res2 = client.post("/api/payments/webhook", json=payload, headers={"x-iyz-signature": "mock_valid_signature"})
    assert res2.status_code == 200 # Should still return 200, but do nothing under the hood
