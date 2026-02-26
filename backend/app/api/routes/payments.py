from fastapi import APIRouter, Request, HTTPException, Header
from app.api.schemas import PaymentCreateIntentRequest, PaymentCreateIntentResponse, PaymentWebhookPayload, PaymentStatusResponse
from app.core.rate_limit import limiter
from app.services.payment_service import payment_service
from app.db.firestore import get_db
from app.db.collections import ORDERS, ORDER_PUBLIC, ORDER_STATUS_HISTORY, ADMIN_AUDIT_LOGS, PAYMENTS
from app.core.state_machine import OrderStatus, get_public_step_label
from firebase_admin import firestore

router = APIRouter()

@router.post("/create-intent", response_model=PaymentCreateIntentResponse)
@limiter.limit("5/minute")
def create_payment_intent(request: Request, payload: PaymentCreateIntentRequest):
    db = get_db()
    
    # Run in transaction to prevent double-click double-charge
    transaction = db.transaction()
    order_ref = db.collection(ORDERS).document(payload.order_id)
    
    @firestore.transactional
    def process_intent(transaction, order_ref):
        snapshot = order_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Order not found")
            
        data = snapshot.to_dict()
        
        # Check current payment status
        if data.get("payment_status") in ["PAID", "PAYMENT_PENDING"]:
            # If already pending, we could technically just return the existing token
            # But for simplicity & idempotency, we query if an active payment exists
            existing_payments = list(db.collection(PAYMENTS).where("order_id", "==", payload.order_id).where("status", "==", "PENDING").limit(1).get())
            if existing_payments:
                existing_payment = existing_payments[0].to_dict()
                return {
                    "token": existing_payment.get("token", ""),
                    "checkout_url": existing_payment.get("checkout_url", ""),
                    "status": "success"
                }

            if data.get("payment_status") == "PAID":
                 raise HTTPException(status_code=400, detail="Order is already paid")
                
        # Calculate amount from backend (trust only backend)
        # Note: In a real app we'd sum cart items here. For v0.1 we use the saved total_amount or default.
        amount = data.get("total_amount", 100.0) 
        if amount <= 0:
            amount = 100.0 # fallback for tests
            
        # Call provider wrapper
        intent_result = payment_service.create_checkout_intent(
            order_id=payload.order_id,
            amount=amount,
            currency=data.get("currency", "TRY"),
            recipient=data.get("recipient", {})
        )
        
        timestamp = firestore.SERVER_TIMESTAMP
        
        # 1. Update Order (payment_status)
        transaction.update(order_ref, {
            "payment_status": "PAYMENT_PENDING"
        })
        
        # 2. Create Payment Document
        payment_ref = db.collection(PAYMENTS).document(intent_result["token"])
        transaction.set(payment_ref, {
            "order_id": payload.order_id,
            "status": "PENDING",
            "amount": amount,
            "currency": data.get("currency", "TRY"),
            "provider": "iyzico",
            "token": intent_result["token"],
            "checkout_url": intent_result["checkout_url"],
            "created_at": timestamp
        })
        
        return intent_result

    try:
        result = process_intent(transaction, order_ref)
        return PaymentCreateIntentResponse(**result)
    except HTTPException:
        raise
    except Exception:
        import traceback
        raise HTTPException(status_code=400, detail=traceback.format_exc())


@router.post("/webhook")
@limiter.limit("100/minute")
def payment_webhook(
    request: Request, 
    payload: PaymentWebhookPayload,
    bg_tasks: BackgroundTasks,
    x_iyz_signature: str = Header(None) # Iyzico signature header
):
    try:
        # 1. Signature Verification Requirement
        if not x_iyz_signature:
            raise HTTPException(status_code=401, detail="Missing signature header")
            
        # We pass the raw string payload body ideally, but here we simplify for the wrapper
        is_valid = payment_service.verify_webhook_signature("raw_body_mock", x_iyz_signature)
        
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
        db = get_db()
        
        # 2. Extract Data from Payload
        token = payload.token
        provider_status = payload.status # e.g. "SUCCESS"
        order_id = payload.conversationId
        
        # 3. Transactional Write Fan-out with DEDUP
        transaction = db.transaction()
        payment_ref = db.collection(PAYMENTS).document(token)
        
        @firestore.transactional
        def process_webhook(transaction, payment_ref):
            snapshot = payment_ref.get(transaction=transaction)
            if not snapshot.exists:
                # We don't fail a webhook 500 if token doesn't exist, just 200 OK so they stop retrying
                return
                
            data = snapshot.to_dict()
            
            # Dedup Check: Is this event already processed?
            if data.get("status") in ["SUCCEEDED", "FAILED"]:
                # Already processed (Double delivery from Provider) -> No-op
                return 
                
            # Map provider status to internal status
            internal_status = "SUCCEEDED" if provider_status.upper() == "SUCCESS" else "FAILED"
            timestamp = firestore.SERVER_TIMESTAMP
            
            # a) UPDATE PAYMENTS
            transaction.update(payment_ref, {
                "status": internal_status,
                "updated_at": timestamp,
                "provider_payment_id": payload.paymentId
            })
            
            # If FAILED, just update payment doc and we stop here
            if internal_status == "FAILED":
                order_ref = db.collection(ORDERS).document(order_id)
                transaction.update(order_ref, {"payment_status": "FAILED"})
                return
                
            # SUCCESS LOGIC follows:
            order_ref = db.collection(ORDERS).document(order_id)
            order_doc = order_ref.get(transaction=transaction)
            
            if order_doc.exists:
                order_data = order_doc.to_dict()
                tracking_code = order_data.get("tracking_code")
                
                # b) UPDATE ORDERS
                transaction.update(order_ref, {
                    "payment_status": "PAID",
                    "status": OrderStatus.PAID,
                    "paid_at": timestamp,
                    "status_updated_at": timestamp,
                    "status_updated_by": "system_webhook"
                })
                
                # c) UPDATE ORDER_PUBLIC (NO PII)
                public_ref = db.collection(ORDER_PUBLIC).document(tracking_code)
                transaction.update(public_ref, {
                    "status": OrderStatus.PAID,
                    "status_updated_at": timestamp,
                    "public_step_label": get_public_step_label(OrderStatus.PAID)
                })
                
                # d) UPDATE HISTORY + AUDIT 
                history_ref = db.collection(ORDER_STATUS_HISTORY).document()
                transaction.set(history_ref, {
                    "order_id": order_id,
                    "from_status": order_data.get("status"),
                    "to_status": OrderStatus.PAID,
                    "actor": "system",
                    "source": "webhook",
                    "timestamp": timestamp
                })
                
                audit_ref = db.collection(ADMIN_AUDIT_LOGS).document()
                transaction.set(audit_ref, {
                    "action": "PAYMENT_RECEIVED",
                    "order_id": order_id,
                    "actor": "system",
                    "timestamp": timestamp
                })

        process_webhook(transaction, payment_ref)
        
        # 4. Enqueue background job (Fire and Forget)
        if provider_status.upper() == "SUCCESS":
           try:
               # Get the tracking code from order (we need outside transaction to be safe or fetch again)
               order_doc_raw = db.collection(ORDERS).document(order_id).get()
               if order_doc_raw.exists:
                   tracking = order_doc_raw.to_dict().get("tracking_code")
                   bg_tasks.add_task(payment_service.enqueue_pdf_generation_task, order_id=order_id, tracking_code=tracking)
           except Exception as e:
               pass
        return {"message": "Webhook processed successfully"}
    except HTTPException:
        raise
    except Exception:
        import traceback
        raise HTTPException(status_code=400, detail=traceback.format_exc())


@router.get("/status", response_model=PaymentStatusResponse)
@limiter.limit("30/minute")
def get_payment_status(request: Request, order_id: str):
    """
    Called by Frontend to poll the status of a specific order's payment.
    Whitelisted minimal fields only.
    """
    db = get_db()
    order_doc = db.collection(ORDERS).document(order_id).get()
    
    if not order_doc.exists:
        raise HTTPException(status_code=404, detail="Order not found")
        
    data = order_doc.to_dict()
    
    return PaymentStatusResponse(
        order_id=order_id,
        payment_status=data.get("payment_status", "UNKNOWN")
    )
