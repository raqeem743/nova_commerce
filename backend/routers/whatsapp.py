import os
from fastapi import APIRouter, HTTPException,Request
from pydantic import BaseModel
from database import conversations_collection,conversation_messages_collection
from datetime import datetime

router=APIRouter()

class WhatsAppMessage(BaseModel):
    customer_phone: str
    message: str
    message_id: str | None = None


# get whatsapp messages
@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(request: Request):

    params = request.query_params

    mode = params.get("hub.mode")
    verify_token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and verify_token == expected_token:
        return int(challenge)

    raise HTTPException(
        status_code=403,
        detail="Webhook verification failed"
    )


# whatsapp webhook
@router.post("/webhooks/whatsapp")
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