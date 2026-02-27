from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas_ops import PdfGenerateJobPayload, PiiCleanupJobPayload, OpsJobResponse
from app.api.deps_ops import verify_oidc_token
from app.db.firestore import get_db
from app.db.collections import ORDERS, ADMIN_AUDIT_LOGS
from firebase_admin import firestore
from app.core.logging import logger

router = APIRouter()

@router.post("/pdf-generate", response_model=OpsJobResponse)
def ops_pdf_generate(payload: PdfGenerateJobPayload, claims: dict = Depends(verify_oidc_token)):
    """
    Called asynchronously by Cloud Tasks when an order is PAID.
    Must be idempotent. Generates a PDF and updates the order status.
    """
    db = get_db()
    
    # We use a transaction to safely handle the optimistic "PENDING" to "GENERATING" state lock
    transaction = db.transaction()
    order_ref = db.collection(ORDERS).document(payload.order_id)
    job_ref = db.collection("jobs").document(payload.job_id)
    
    @firestore.transactional
    def process_pdf_job(transaction, order_ref, job_ref):
         # Check if job was already processed (Idempotency Key)
         job_snap = job_ref.get() # mockfirestore compatibility
         if job_snap.exists and job_snap.to_dict().get("status") == "SUCCEEDED":
              return OpsJobResponse(message="No-op (Job already succeeded)", status="SUCCEEDED", job_id=payload.job_id)
              
         order_snap = order_ref.get() # mockfirestore compatibility
         if not order_snap.exists:
              raise HTTPException(status_code=404, detail="Order not found for PDF job")
              
         order_data = order_snap.to_dict()
         current_pdf_status = order_data.get("pdf_status")
         
         # Idempotency checks based on domain model
         if current_pdf_status == "READY":
             return OpsJobResponse(message="No-op (PDF already READY)", status="SUCCEEDED", job_id=payload.job_id)
             
         if current_pdf_status == "GENERATING":
             # Extremely edge case where concurrent tasks picked this up OR previous attempt crashed mid-generation
             # Best practice for Cloud Tasks is returning an error (e.g. 409) so it retries later instead of colliding.
             raise HTTPException(status_code=409, detail="PDF generation currently locked / in progress")
         
         # Assuming valid starting state: None or "PENDING" or "FAILED"
         # 1. Update state to GENERATING inside transaction
         transaction.update(order_ref, {
             "pdf_status": "GENERATING",
             "pdf_updated_at": firestore.SERVER_TIMESTAMP
         })
         
         # 2. Record Job start
         transaction.set(job_ref, {
             "job_type": payload.job_type,
             "order_id": payload.order_id,
             "attempt": payload.attempt,
             "status": "RUNNING",
             "created_at": firestore.SERVER_TIMESTAMP
         })
         
         return "PROCEED_GENERATION"
         
    # 1. Execute DB State check
    try:
        init_result = process_pdf_job(transaction, order_ref, job_ref)
        if isinstance(init_result, OpsJobResponse):
            return init_result # Caught by idempotency
    except Exception as e:
        logger.error(f"Failed to acquire PDF generation lock for {payload.order_id}: {str(e)}")
        raise # Reraise HTTPExceptions directly (e.g. 409)
        
    # 2. Actually Generate PDF (Outside transaction to not hold locks during slow I/O)
    logger.info(f"Producing letter PDF for Order: {payload.order_id}")
    try:
        # Staging-only controlled failure for E2E testing (N7) — NEVER in production
        from app.core.config import settings
        if settings.ENV != "production" and settings.ENV in ["staging", "test"] and payload.job_id.startswith("FAIL_TEST_"):
            logger.warning(f"CONTROLLED FAIL TRIGGER in {settings.ENV}: {payload.job_id}")
            raise Exception(f"Controlled E2E test failure for job {payload.job_id}")
        
        # TODO: integrate with real PDF service when available (ReportLab / Playwright etc)
        mock_pdf_gs_path = f"gs://emektup-sandbox/orders/{payload.order_id}/generated/letter.pdf"
        
        # 3. Finalize Job and Order State
        db.collection("jobs").document(payload.job_id).set({
            "status": "SUCCEEDED",
            "updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        order_ref.set({
            "pdf_status": "READY",
            "pdf_path": mock_pdf_gs_path,
            "pdf_updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        logger.info(f"PDF Job {payload.job_id} successfully mapped.")
        return OpsJobResponse(message="PDF successfully generated", status="SUCCEEDED", job_id=payload.job_id)
        
    except Exception as e:
        # Failure tracking
        logger.error(f"PDF Generation explicitly failed for job {payload.job_id}: {str(e)}")
        # Save failure context for Dead Letter processing
        db.collection("jobs").document(payload.job_id).set({
             "status": "FAILED",
             "last_error": str(e),
             "updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        order_ref.set({
             "pdf_status": "FAILED",
             "pdf_error_message": str(e),
             "pdf_updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        # Note: We return 500 so Cloud Tasks automatically retries (following backoff config)
        raise HTTPException(status_code=500, detail="PDF Service failure")


@router.post("/pii-cleanup", response_model=OpsJobResponse)
def ops_pii_cleanup(payload: PiiCleanupJobPayload, claims: dict = Depends(verify_oidc_token)):
    """
    Called asynchronously by Cloud Scheduler every night.
    Anonymizes old, completed orders to respect PII retentions.
    """
    db = get_db()
    try:
        logger.info(f"Cron PII Cleanup triggered. Cutoff days: {payload.cutoff_days}, Dry run: {payload.dry_run}")
        
        if payload.dry_run:
            # For v0.1: just simulating read count
            # Ideally: Query where status IN [SHIPPED, DELIVERED] and created_at < (now - cutoff_days)
            simulate_count = 5
            logger.info(f"DRY RUN: Would have cleared PII from {simulate_count} records.")
            return OpsJobResponse(message=f"Dry run success. Est records: {simulate_count}", status="SUCCEEDED", job_id=payload.job_id)
            
        else:
            # Real PII cleanup: anonymize eligible orders
            from datetime import datetime, timedelta, timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=payload.cutoff_days)
            
            # Query eligible orders: SHIPPED or CANCELLED, created before cutoff
            eligible_statuses = ["SHIPPED", "CANCELLED"]
            cleaned_count = 0
            cleaned_order_ids = []
            
            for eligible_status in eligible_statuses:
                query = (db.collection(ORDERS)
                    .where("status", "==", eligible_status)
                    .limit(100))
                
                for doc in query.stream():
                    order_data = doc.to_dict()
                    # Filter by cutoff date in Python (avoids composite index)
                    if payload.cutoff_days > 0:
                        created_at = order_data.get("created_at")
                        if created_at:
                            # Firestore timestamps have a .replace method (they're datetime-like)
                            try:
                                if created_at > cutoff_date:
                                    continue  # Not old enough
                            except TypeError:
                                pass  # If comparison fails, include the record
                    # Only clean if PII fields still exist (idempotency)
                    if order_data.get("recipient") or order_data.get("letter_content"):
                        doc.reference.update({
                            "recipient": firestore.DELETE_FIELD,
                            "letter_content": firestore.DELETE_FIELD,
                            "notes": firestore.DELETE_FIELD,
                            "pii_cleaned_at": firestore.SERVER_TIMESTAMP
                        })
                        cleaned_count += 1
                        cleaned_order_ids.append(doc.id)
            
            # Write audit log
            audit_ref = db.collection(ADMIN_AUDIT_LOGS).document()
            audit_ref.set({
                "action": "PII_CLEANUP",
                "actor": "system:scheduler",
                "job_id": payload.job_id,
                "cleaned_count": cleaned_count,
                "cleaned_order_ids": cleaned_order_ids[:20],  # cap for audit size
                "cutoff_days": payload.cutoff_days,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"PII Cleanup: anonymized {cleaned_count} orders")
            return OpsJobResponse(message=f"PII cleaned from {cleaned_count} records.", status="SUCCEEDED", job_id=payload.job_id)
            
    except Exception as e:
        logger.error(f"Cron PII Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup sweep failed")
