import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.collections import ORDERS
from unittest.mock import patch
from app.core.config import settings
import mockfirestore

mock_db = mockfirestore.MockFirestore()

# Make sure tests use the mock environment so OIDC mock-token passes
settings.ENV = "test"

@pytest.fixture(autouse=True)
def reset_mock_db():
    mock_db.reset()
    yield

@pytest.mark.asyncio
@patch("app.api.routes.ops.get_db", return_value=mock_db)
async def test_ops_require_oidc_token(mock_get_db):
    """Verify that Ops endpoints reject unauthorized traffic."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/ops/pdf-generate", json={
            "job_id": "test_123",
            "order_id": "ord_123"
        })
        # HTTPBearer correctly returns 403 if it's completely missing, or 401 in some cases.
        assert response.status_code in (401, 403)

@pytest.mark.asyncio
@patch("app.api.routes.ops.get_db", return_value=mock_db)
async def test_ops_pdf_generate_idempotency_and_success(mock_get_db_ops):
    """Verify order PDF generation locks and succeeds under local mock auth."""
    # First, setup dummy order in Mock Firestore
    order_id = "test_order_pdf"
    mock_db.collection(ORDERS).document(order_id).set({
        "status": "PAID"
    })
    
    auth_headers = {"Authorization": "Bearer ops-mock-token"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Trigger fresh PDF Generation
        response = await ac.post("/api/ops/pdf-generate", json={
            "job_id": "job_111",
            "order_id": order_id
        }, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "PDF successfully generated"
        
        # Verify db state
        order_doc = mock_db.collection(ORDERS).document(order_id).get().to_dict()
        assert order_doc["pdf_status"] == "READY"
        assert "emektup-sandbox" in order_doc["pdf_path"]
        
        # 2. Trigger AGAIN with same JOB ID (Idempotency - No-op via DB check)
        response_dup = await ac.post("/api/ops/pdf-generate", json={
            "job_id": "job_111",
            "order_id": order_id
        }, headers=auth_headers)
        
        assert response_dup.status_code == 200
        assert "No-op" in response_dup.json()["message"]
        assert response_dup.json()["status"] == "SUCCEEDED"

@pytest.mark.asyncio
@patch("app.api.routes.ops.get_db", return_value=mock_db)
async def test_ops_pii_cleanup_dry_run(mock_get_db_ops):
    auth_headers = {"Authorization": "Bearer ops-mock-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/ops/pii-cleanup", json={
            "job_id": "job_pii_123",
            "dry_run": True
        }, headers=auth_headers)
        
        assert response.status_code == 200
        assert "Dry run success" in response.json()["message"]
