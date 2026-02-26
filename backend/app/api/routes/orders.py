from fastapi import APIRouter, Request, HTTPException, status
from app.api.schemas import OrderCreateRequest, OrderCreateResponse, OrderPublicResponse
from app.core.rate_limit import limiter
from app.core.utils import generate_tracking_code
from app.db.firestore import get_db
from app.db.collections import ORDERS, ORDER_PUBLIC, ORDER_STATUS_HISTORY, ADMIN_AUDIT_LOGS
from firebase_admin import firestore

router = APIRouter()

@router.post("/create", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_order(request: Request, payload: OrderCreateRequest):
    db = get_db()
    
    # 1. Simple Idempotency by client_request_id (check if exists)
    if payload.client_request_id:
        existing_orders = list(db.collection(ORDERS).where("client_request_id", "==", payload.client_request_id).limit(1).get())
        if existing_orders:
            existing = existing_orders[0].to_dict()
            return OrderCreateResponse(
                order_id=existing_orders[0].id,
                tracking_code=existing["tracking_code"],
                status=existing["status"]
            )

    # 2. Setup Order Information
    tracking_code = generate_tracking_code()
    order_ref = db.collection(ORDERS).document()
    order_id = order_ref.id
    timestamp = firestore.SERVER_TIMESTAMP
    
    # 3. Firestore Batch (Atomic Operation for the 4 records)
    batch = db.batch()
    
    # a) orders/{orderId} (PRIVATE)
    order_data = {
        "status": "CREATED",
        "is_guest": payload.is_guest,
        "user_id": payload.user_id,
        "total_amount": 0.0,
        "currency": "TRY",
        "recipient": payload.recipient.model_dump(),
        "letter_content": payload.letter_content,
        "notes": payload.notes,
        "tracking_code": tracking_code,
        "client_request_id": payload.client_request_id,
        "created_at": timestamp,
        "status_updated_at": timestamp
    }
    batch.set(order_ref, order_data)
    
    # b) order_public/{tracking_code} (PUBLIC) - STRICTLY NO PII
    public_ref = db.collection(ORDER_PUBLIC).document(tracking_code)
    public_data = {
        "order_id": order_id,
        "status": "CREATED",
        "created_at": timestamp,
        "public_step_label": "Sipariş Alındı"
    }
    batch.set(public_ref, public_data)
    
    # c) order_status_history/{history_id}
    history_ref = db.collection(ORDER_STATUS_HISTORY).document()
    history_data = {
        "order_id": order_id,
        "from_status": None,
        "to_status": "CREATED",
        "actor": "system",
        "timestamp": timestamp
    }
    batch.set(history_ref, history_data)
    
    # d) admin_audit_logs/{log_id}
    audit_ref = db.collection(ADMIN_AUDIT_LOGS).document()
    audit_data = {
        "action": "ORDER_CREATED",
        "order_id": order_id,
        "actor": "system",
        "timestamp": timestamp
    }
    batch.set(audit_ref, audit_data)
    
    # 4. Commit batch
    batch.commit()
    
    return OrderCreateResponse(
        order_id=order_id,
        tracking_code=tracking_code,
        status="CREATED"
    )

@router.get("/track/{tracking_code}", response_model=OrderPublicResponse)
@limiter.limit("20/minute")
def track_order(request: Request, tracking_code: str):
    db = get_db()
    
    public_doc = db.collection(ORDER_PUBLIC).document(tracking_code).get()
    
    if not public_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking code not found"
        )
        
    data = public_doc.to_dict()
    
    # Format the server timestamp for the response
    created_at_dt = data.get("created_at")
    created_at_str = created_at_dt.isoformat() if hasattr(created_at_dt, "isoformat") else str(created_at_dt)
    
    return OrderPublicResponse(
        tracking_code=tracking_code,
        status=data.get("status", "UNKNOWN"),
        created_at=created_at_str,
        public_step_label=data.get("public_step_label")
    )
