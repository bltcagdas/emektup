from pydantic import BaseModel, Field, constr
from typing import Optional, List, Dict, Any
from datetime import datetime

class RecipientInfo(BaseModel):
    name: str = Field(..., max_length=100)
    address: str = Field(..., max_length=500)
    phone: Optional[str] = Field(None, max_length=20)

class OrderCreateRequest(BaseModel):
    client_request_id: Optional[str] = Field(None, description="Idempotency key")
    is_guest: bool = True
    user_id: Optional[str] = None
    recipient: RecipientInfo
    # Sanitization limits: maximum 20000 characters for letter content to prevent abuse
    letter_content: str = Field(..., max_length=20000, description="The content of the letter")
    notes: Optional[str] = Field(None, max_length=1000)

class OrderCreateResponse(BaseModel):
    order_id: str
    tracking_code: str
    status: str

class OrderPublicResponse(BaseModel):
    tracking_code: str
    status: str
    created_at: str
    public_step_label: Optional[str] = None

# --- ADMIN SCHEMAS --- 

class AdminOrderListItem(BaseModel):
    order_id: str
    tracking_code: str
    created_at: str
    status: str
    status_updated_at: str
    total_amount: float
    is_guest: bool
    user_id: Optional[str] = None
    recipient_summary: Optional[str] = None # E.g "Silivri, Istanbul" (No full PII)

class AdminOrderListResponse(BaseModel):
    items: List[AdminOrderListItem]
    next_cursor: Optional[str] = None # Cursor based pagination
    has_more: bool

class AdminOrderStatusUpdateRequest(BaseModel):
    to_status: str
    expected_from_status: str # Optimistic Locking
    note: Optional[str] = None

# --- PAYMENT SCHEMAS ---

class PaymentCreateIntentRequest(BaseModel):
    order_id: str
    client_request_id: Optional[str] = None

class PaymentCreateIntentResponse(BaseModel):
    token: str
    checkout_url: str
    status: str

class PaymentWebhookPayload(BaseModel):
    token: str
    status: str
    paymentId: Optional[str] = None
    conversationId: Optional[str] = None # We map this to order_id

class PaymentStatusResponse(BaseModel):
    order_id: str
    payment_status: str


