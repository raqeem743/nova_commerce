from datetime import datetime
from typing import Optional
from fastapi import  HTTPException,APIRouter,Request
from pydantic import BaseModel, Field
from routers.cart import PyObjectId
from database import orders_collection,payment_attempts_collection
from bson import ObjectId
import stripe
import os

router=APIRouter(
    prefix="/payments",
    responses={404: {"description": "Not found"}},
)

class PaymentCreate(BaseModel):
    order_id: Optional[PyObjectId] = Field(alias="_id", default=None)

# payment checkout
@router.post( path="/checkout",
    summary="Create checkout",
    description="Create a checkout",
    response_model=PaymentCreate)

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

# Stripe webhook
@router.post(path="/",
    summary="stripe webhook",
    description="stripe webhook",
    response_model=PaymentCreate)

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

# get payments by id
@router.get(path="/{order_id}",
    summary="get payment",
    description="get payment by id",
    response_model=PaymentCreate)

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