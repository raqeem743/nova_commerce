from datetime import datetime
import os
import stripe
from fastapi import FastAPI, HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId, utc

from database import products_collection,orders_collection,payment_attempts_collection,conversations_collection,conversation_messages_collection
from models.basemodels import  PaymentCreate
from models.products import router as products_router
from models.products import router as cart_router
from models.products import router as checkout_router

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

app.include_router(products_router)
app.include_router(cart_router)
app.include_router(checkout_router)

@app.get("/")
def home():
    return {
        "message": "NOVA Commerce API is running"
    }

# payment checkout
@app.post("/payments/create-checkout")
def create_checkout(payment: PaymentCreate):

    # Find the order
    try:
        order = orders_collection.find_one({
            "_id": ObjectId(payment.order_id)
        })
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid order ID"
        )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Only online card payments are allowed here
    if order["payment"]["method"] != "online_card":
        raise HTTPException(
            status_code=400,
            detail="This order does not require online card payment"
        )

    # Don't create another payment for an already paid order
    if order["payment"]["status"] == "paid":
        raise HTTPException(
            status_code=400,
            detail="Order is already paid"
        )

    try:

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],

            line_items=[
                {
                    "price_data": {
                        "currency": "pkr",
                        "product_data": {
                            "name": item["name"]
                        },
                        "unit_amount": int(item["unit_price"] * 100)
                    },
                    "quantity": item["quantity"]
                }
                for item in order["items"]
            ],

            mode="payment",

            customer_email=order["customer"]["email"],

            metadata={
                "order_id": str(order["_id"]),
                "order_number": order["order_number"]
            },

            success_url="http://localhost:5173/order-success?order_id="
                        + str(order["_id"]),

            cancel_url="http://localhost:5173/payment-cancelled?order_id="
                        + str(order["_id"])
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Stripe error: {str(e)}"
        )

    # Save payment attempt
    payment_attempt = {
        "order_id": str(order["_id"]),
        "order_number": order["order_number"],
        "provider": "stripe",
        "session_id": session.id,
        "status": "pending",
        "amount": order["pricing"]["total"],
        "currency": "pkr"
    }

    payment_attempts_collection.insert_one(payment_attempt)

    return {
        "message": "Payment checkout created",
        "order_id": str(order["_id"]),
        "order_number": order["order_number"],
        "checkout_url": session.url,
        "session_id": session.id
    }


@app.post("/payments/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()

    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature"
        )

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            webhook_secret
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload"
        )

    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=400,
            detail="Invalid Stripe signature"
        )

    # Payment completed
    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]

        order_id = session["metadata"].get("order_id")

        if order_id:

            orders_collection.update_one(
                {
                    "_id": ObjectId(order_id)
                },
                {
                    "$set": {
                        "status": "confirmed",
                        "payment.status": "paid",
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            payment_attempts_collection.update_one(
                {
                    "session_id": session["id"]
                },
                {
                    "$set": {
                        "status": "paid"
                    }
                }
            )

    elif event["type"] == "checkout.session.expired":

        session = event["data"]["object"]

        order_id = session["metadata"].get("order_id")

        if order_id:

            orders_collection.update_one(
            {
                "_id": ObjectId(order_id)
            },
            {
                "$set": {
                    "payment.status": "failed",
                    "updated_at": datetime.utcnow()
                }
            }
        )

        payment_attempts_collection.update_one(
            {
                "session_id": session["id"]
            },
            {
                "$set": {
                    "status": "failed"
                }
            }
        )

    return {
        "received": True
    }


@app.get("/payments/{order_id}")
def get_payment_status(order_id: str):

    try:
        order = orders_collection.find_one({
            "_id": ObjectId(order_id)
        })
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid order ID"
        )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "order_id": str(order["_id"]),
        "order_number": order["order_number"],
        "order_status": order["status"],
        "payment": order["payment"]
    }

# admin stats panel
@app.get("/admin/stats")
def get_admin_stats():

    total_orders = orders_collection.count_documents({})

    pending_orders = orders_collection.count_documents({
        "status": {
            "$in": [
                "pending_payment",
                "confirmed",
                "preparing",
                "ready"
            ]
        }
    })

    delivered_orders = orders_collection.count_documents({
        "status": "delivered"
    })

    cancelled_orders = orders_collection.count_documents({
        "status": "cancelled"
    })

    total_products = products_collection.count_documents({})

    low_stock_products = products_collection.count_documents({
        "stock": {
            "$lte": 5
        }
    })

    # Calculate revenue from delivered orders
    revenue_result = list(
        orders_collection.aggregate([
            {
                "$match": {
                    "status": "delivered"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {
                        "$sum": "$pricing.total"
                    }
                }
            }
        ])
    )

    total_revenue = 0

    if revenue_result:
        total_revenue = revenue_result[0]["total"]

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "total_revenue": total_revenue
    }

# admin get all orders
@app.get("/admin/orders")
def get_admin_orders(
    status: str | None = None
):

    query = {}

    if status:
        query["status"] = status

    orders = list(
        orders_collection.find(query).sort(
            "created_at",
            -1
        )
    )

    result = []

    for order in orders:

        result.append({
            "id": str(order["_id"]),
            "order_number": order["order_number"],
            "customer": order["customer"],
            "items": order["items"],
            "pricing": order["pricing"],
            "delivery": order["delivery"],
            "payment": order["payment"],
            "status": order["status"],
            "source": order["source"],
            "created_at": order["created_at"],
            "updated_at": order["updated_at"]
        })

    return {
        "orders": result,
        "count": len(result)
    }

# admin get order by order_id
@app.get("/admin/orders/{order_id}")
def get_admin_order(order_id: str):

    try:
        order = orders_collection.find_one({
            "_id": ObjectId(order_id)
        })
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid order ID"
        )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "id": str(order["_id"]),
        "order_number": order["order_number"],
        "customer": order["customer"],
        "items": order["items"],
        "delivery": order["delivery"],
        "pricing": order["pricing"],
        "payment": order["payment"],
        "status": order["status"],
        "source": order["source"],
        "created_at": order["created_at"],
        "updated_at": order["updated_at"]
    }

# admin get low stock product
@app.get("/admin/products/low-stock")
def get_low_stock_products():

    products = list(
        products_collection.find({
            "stock": {
                "$lte": 5
            }
        }).sort(
            "stock",
            1
        )
    )

    result = []

    for product in products:

        result.append({
            "id": str(product["_id"]),
            "name": product["name"],
            "price": product["price"],
            "category": product["category"],
            "stock": product["stock"],
            "image": product.get("image", "")
        })

    return {
        "products": result,
        "count": len(result)
    }

# get whatsapp messages
@app.get("/webhooks/whatsapp")
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
