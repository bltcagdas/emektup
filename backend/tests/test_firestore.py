import pytest
from mockfirestore import MockFirestore
from app.db.collections import ORDERS

# Patch the get_db function to return a MockFirestore client
@pytest.fixture
def mock_db(monkeypatch):
    mock = MockFirestore()
    monkeypatch.setattr("app.db.firestore.get_db", lambda: mock)
    return mock

def test_firestore_smoke(mock_db):
    """
    Simulates writing and reading a document to verify 
    the Firestore abstraction wrapper logic works without touching Production.
    """
    doc_ref = mock_db.collection(ORDERS).document("test_order_123")
    
    # 1. Write document
    doc_ref.set({
        "status": "CREATED",
        "total_amount": 150.0,
        "is_guest": True
    })
    
    # 2. Read document
    doc_snapshot = doc_ref.get()
    
    # 3. Assertions
    assert doc_snapshot.exists
    
    data = doc_snapshot.to_dict()
    assert data["status"] == "CREATED"
    assert data["total_amount"] == 150.0
    assert data["is_guest"] is True
    
    # 4. Clean up mock
    doc_ref.delete()
    
    # mockfirestore raises KeyError when trying to get a deleted document
    try:
        doc_ref.get()
        assert False, "Document should have been deleted"
    except Exception:
        pass
