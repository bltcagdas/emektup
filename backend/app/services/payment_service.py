from typing import Dict, Any
from app.core.config import settings

class PaymentService:
    def __init__(self):
        self.env = settings.IYZICO_ENV
        self.api_key = settings.IYZICO_API_KEY
        self.secret_key = settings.IYZICO_SECRET_KEY
        self.base_url = settings.IYZICO_BASE_URL

    def create_checkout_intent(self, order_id: str, amount: float, currency: str = "TRY", recipient: Dict = None) -> Dict[str, Any]:
        """
        Creates a payment intent (e.g., Iyzico Checkout Form Initializer).
        Since this is an agnostic wrapper, we mock the HTTP call for now.
        In a real scenario, we'd use httpx to POST to self.base_url + "/payment/iyziup/initialize".
        """
        # Mocking the provider logic
        if self.env == "sandbox" and self.api_key == "mock_api_key":
            return {
                "status": "success",
                "token": f"sandbox_token_{order_id}",
                "checkout_url": f"https://sandbox-checkout.iyzipay.com/token=sandbox_token_{order_id}"
            }
            
        # Real HTTP logic would go here
        raise NotImplementedError("Live Iyzico HTTP calls not fully implemented yet.")

    def verify_webhook_signature(self, payload_body: str, signature_header: str) -> bool:
        """
        Verifies the incoming webhook signature from Iyzico.
        Mock implementation for tests: if token equals "sandbox_token_...", return True.
        """
        if self.env == "sandbox" and signature_header == "mock_valid_signature":
            return True
            
        # Iyzico signature logic is typically x-iyz-signature 
        # but let's assume a standard HMAC SHA256 for the wrapper contract.
        # return hmac.compare_digest(expected_sig, signature_header)
        return False
        
    def enqueue_pdf_generation_task(self, order_id: str, tracking_code: str = None) -> None:
        """
        Enqueues a PDF generation task to Google Cloud Tasks for async processing.
        Local/Test environments just skip the actual GCP API call but log the action.
        """
        if settings.ENV in ["local", "development", "test"]:
            from app.core.logging import logger
            logger.info(f"Local ENV: Mock enqueueing PDF task for Order {order_id}")
            return
            
        try:
            from google.cloud import tasks_v2
            import json
            import uuid
            
            client = tasks_v2.CloudTasksClient()
            
            # These would ideally be configured in settings for a highly flexible environment
            project = settings.FIREBASE_PROJECT_ID 
            location = "europe-west1" # Matches your Cloud Run location usually
            queue = "ops-pdf-generate"
            
            parent = client.queue_path(project, location, queue)
            
            url = f"{settings.OPS_AUDIENCE_URL}/api/ops/pdf-generate"
            
            job_id = f"pdf_{order_id}_{uuid.uuid4().hex[:8]}"
            payload = {
                "job_type": "pdf_generate",
                "job_id": job_id,
                "order_id": order_id,
                "tracking_code": tracking_code,
                "requested_by": "system:webhook",
                "attempt": 1
            }
            
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": url,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(payload).encode(),
                    "oidc_token": {
                        "service_account_email": settings.OPS_SERVICE_ACCOUNT_EMAIL,
                        "audience": settings.OPS_AUDIENCE_URL,
                    },
                }
            }
            
            response = client.create_task(request={"parent": parent, "task": task})
            from app.core.logging import logger
            logger.info(f"Successfully enqueued Cloud Task {response.name} for Order {order_id}")
        except Exception as e:
            from app.core.logging import logger
            logger.error(f"Failed to enqueue Cloud Task for order {order_id}: {str(e)}")
            # In production, we might want to alert Sentry here

payment_service = PaymentService()
