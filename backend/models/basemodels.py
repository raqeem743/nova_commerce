from pydantic import BaseModel

class WhatsAppMessage(BaseModel):
    customer_phone: str
    message: str
    message_id: str | None = None