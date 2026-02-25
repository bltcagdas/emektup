from typing import Dict, List, Optional
from pydantic import BaseModel

# Fixed Production Status Set for v0.1
class OrderStatus:
    CREATED = "CREATED"
    PAID = "PAID"
    READY_FOR_PRINT = "READY_FOR_PRINT"
    PRINTED = "PRINTED"
    READY_FOR_PTT = "READY_FOR_PTT"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"

# Define Allowed Transitions (From -> To)
# E.g., You can only go to READY_FOR_PRINT if you are currently PAID.
ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    OrderStatus.CREATED: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.READY_FOR_PRINT, OrderStatus.CANCELLED],
    OrderStatus.READY_FOR_PRINT: [OrderStatus.PRINTED, OrderStatus.CANCELLED],
    OrderStatus.PRINTED: [OrderStatus.READY_FOR_PTT],
    OrderStatus.READY_FOR_PTT: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [], # End of line
    OrderStatus.CANCELLED: [] # End of line
}

def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Checks if a status transition is allowed according to the State Machine rules."""
    allowed = ALLOWED_TRANSITIONS.get(from_status, [])
    return to_status in allowed

def get_public_step_label(status: str) -> str:
    """Maps internal system statuses to user-friendly public step labels."""
    mapping = {
        OrderStatus.CREATED: "Sipariş Alındı (Ödeme Bekleniyor)",
        OrderStatus.PAID: "Ödeme Onaylandı, Hazırlanıyor",
        OrderStatus.READY_FOR_PRINT: "Baskı Sırasında",
        OrderStatus.PRINTED: "Baskı Tamamlandı",
        OrderStatus.READY_FOR_PTT: "Kargoya Verilmek Üzere Bekliyor",
        OrderStatus.SHIPPED: "Kargoya Verildi",
        OrderStatus.CANCELLED: "İptal Edildi"
    }
    return mapping.get(status, "Bilinmeyen Durum")
