from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class CartItemUpdate(BaseModel):
    quantity:int =Field(ge=0)


class CartItemCreate(BaseModel):
    product_id:str
    quantity:int =Field(default=0,ge=0)

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

class PaymentCreate(BaseModel):
    order_id: str

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
    
class WhatsAppMessage(BaseModel):
    customer_phone: str
    message: str
    message_id: str | None = None