from datetime import datetime
import os
import stripe
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from database import conversations_collection,conversation_messages_collection
from models.products import router as products_router
from models.cart import router as cart_router
from models.checkout import router as checkout_router
from models.orders import router as orders_router
from models.payments import router as payments_router
from models.admin import router as admin_router


from dotenv import load_dotenv
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router,admin_router,cart_router,checkout_router,orders_router,payments_router)

@app.get("/")
def home():
    return {
        "message": "NOVA Commerce API is running"
    }


# whatsapp webhook
@app.post("/webhooks/whatsapp")
async def receive_whatsapp_message(request: Request):

    data = await request.json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages", [])

        if not messages:
            return {
                "message": "Webhook received",
                "status": "no_message"
            }

        message = messages[0]

        customer_phone = message["from"]
        message_id = message["id"]
        message_type = message["type"]

        if message_type != "text":
            return {
                "message": "Webhook received",
                "status": "unsupported_message_type",
                "message_type": message_type
            }

        message_text = message["text"]["body"]

        conversation = conversations_collection.find_one({
            "customer_phone": customer_phone,
            "channel": "whatsapp"
        })

        if not conversation:

            conversation_document = {
                "customer_phone": customer_phone,
                "channel": "whatsapp",
                "state": "new",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = conversations_collection.insert_one(
                conversation_document
            )

            conversation_id = str(result.inserted_id)

        else:

            conversation_id = str(conversation["_id"])

            conversations_collection.update_one(
                {"_id": conversation["_id"]},
                {
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )

        message_document = {
            "conversation_id": conversation_id,
            "customer_phone": customer_phone,
            "channel": "whatsapp",
            "sender": "customer",
            "message": message_text,
            "message_id": message_id,
            "message_type": message_type,
            "created_at": datetime.utcnow()
        }

        conversation_messages_collection.insert_one(
            message_document
        )

        return {
            "message": "WhatsApp message received successfully",
            "conversation_id": conversation_id,
            "customer_phone": customer_phone,
            "text": message_text,
            "status": "saved"
        }

    except Exception as e:

        return {
            "message": "Webhook received but could not process message",
            "status": "error",
            "error": str(e)
        }
