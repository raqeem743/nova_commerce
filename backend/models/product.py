from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from typing import Literal


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float = Field(gt=0)
    category: str
    image: str
    stock: int = Field(default=0, ge=0)
    featured: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    image: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)
    featured: Optional[bool] = None

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