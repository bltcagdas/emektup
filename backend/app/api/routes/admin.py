from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from firebase_admin import firestore
from app.api.deps import require_admin, UserRecord
from app.api.schemas import AdminOrderListResponse, AdminOrderListItem, AdminOrderStatusUpdateRequest
from app.db.firestore import get_db
from app.db.collections import ORDERS, ORDER_PUBLIC, ORDER_STATUS_HISTORY, ADMIN_AUDIT_LOGS
from app.core.state_machine import is_valid_transition, get_public_step_label
import datetime

router = APIRouter(dependencies=[Depends(require_admin)])

@router.get("/orders", response_model=AdminOrderListResponse)
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Document ID of the last item for pagination")
):
    db = get_db()
    
    # Base query: Order by created_at descending
    query = db.collection(ORDERS).order_by("created_at", direction=firestore.Query.DESCENDING)
    
    # Filtering (Requires Composite Indexes in Firestore)
    if status_filter:
        query = query.where(filter=firestore.FieldFilter("status", "==", status_filter))
        
    query = query.limit(limit)
    
    # Cursor Pagination logic
    if cursor:
        cursor_doc = db.collection(ORDERS).document(cursor).get()
        if cursor_doc.exists:
            query = query.start_after(cursor_doc)
            
    docs = list(query.get())
    
    items = []
    for doc in docs:
        data = doc.to_dict()
        
        # Format Timestamps
        created_at = data.get("created_at")
        status_updated_at = data.get("status_updated_at", created_at)
        c_str = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        s_str = status_updated_at.isoformat() if hasattr(status_updated_at, "isoformat") else str(status_updated_at)
        
        # Safely extract minimal summary
        recipient = data.get("recipient", {})
        # Note: A real app might parse the city/state, here we just truncate safely
        addr = recipient.get("address", "")
        summary = addr[:30] + "..." if len(addr) > 30 else addr
        
        items.append(AdminOrderListItem(
            order_id=doc.id,
            tracking_code=data.get("tracking_code", ""),
            created_at=c_str,
            status=data.get("status", "UNKNOWN"),
            status_updated_at=s_str,
            total_amount=data.get("total_amount", 0.0),
            is_guest=data.get("is_guest", True),
            user_id=data.get("user_id"),
            recipient_summary=summary
        ))
        
    has_more = len(docs) == limit
    next_cursor = docs[-1].id if has_more and docs else None
    
    return AdminOrderListResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more
    )

@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: str, 
    payload: AdminOrderStatusUpdateRequest,
    admin_user: UserRecord = Depends(require_admin)
):
    db = get_db()
    
    # Run the entire status update inside a Firestore Transaction
    # This guarantees Optimistic Locking + Atomic Fan-out Writes
    transaction = db.transaction()
    order_ref = db.collection(ORDERS).document(order_id)
    
    @firestore.transactional
    def update_in_transaction(transaction, order_ref):
        snapshot = order_ref.get(transaction=transaction)
        
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Order not found")
            
        data = snapshot.to_dict()
        current_status = data.get("status")
        tracking_code = data.get("tracking_code")
        
        # 1. Optimistic Locking Check (Expected vs Current)
        if current_status != payload.expected_from_status:
            # According to specs, return a 409 Conflict with details
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "STATUS_MISMATCH",
                    "current_status": current_status,
                    "message": f"Expected status {payload.expected_from_status} but order is currently in {current_status}"
                }
            )
            
        # 2. State Machine Rule Engine Check
        if not is_valid_transition(current_status, payload.to_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from {current_status} to {payload.to_status}"
            )
            
        timestamp = firestore.SERVER_TIMESTAMP
        
        # 3. Perform the Atomic Writes
        
        # a) orders.status
        transaction.update(order_ref, {
            "status": payload.to_status,
            "status_updated_at": timestamp,
            "status_updated_by": admin_user.uid
        })
        
        # b) order_public (NO PII)
        public_ref = db.collection(ORDER_PUBLIC).document(tracking_code)
        transaction.update(public_ref, {
            "status": payload.to_status,
            "status_updated_at": timestamp,
            "public_step_label": get_public_step_label(payload.to_status)
        })
        
        # c) order_status_history
        history_ref = db.collection(ORDER_STATUS_HISTORY).document()
        transaction.set(history_ref, {
            "order_id": order_id,
            "from_status": current_status,
            "to_status": payload.to_status,
            "actor": f"admin_{admin_user.uid}",
            "source": "admin_panel",
            "timestamp": timestamp,
            "note": payload.note
        })
        
        # d) admin_audit_logs
        audit_ref = db.collection(ADMIN_AUDIT_LOGS).document()
        transaction.set(audit_ref, {
            "action": "ORDER_STATUS_CHANGE",
            "order_id": order_id,
            "actor": admin_user.uid,
            "metadata": {
                "from": current_status,
                "to": payload.to_status
            },
            "timestamp": timestamp
        })
        
        return current_status
        
    # Execute transaction
    old_status = update_in_transaction(transaction, order_ref)
    
    return {
        "message": "Status updated successfully",
        "order_id": order_id,
        "previous_status": old_status,
        "new_status": payload.to_status
    }
