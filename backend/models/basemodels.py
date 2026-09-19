from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class CheckoutRequest(BaseModel):
    customer_id: str
    name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    postcode: str


class OrderCreate(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    address: str
    city: str
    postcode: str
    payment_method: Literal[
        "online_card",
        "cash_on_delivery",
        "card_on_delivery"
    ]

class OrderStatusUpdate(BaseModel):
    status: Literal[
        "pending_payment",
        "confirmed",
        "preparing",
        "ready",
        "dispatched",
        "delivered",
        "cancelled"
    ]

class PaymentCreate(BaseModel):
    order_id: str
    
class WhatsAppMessage(BaseModel):
    customer_phone: str
    message: str
    message_id: str | None = None