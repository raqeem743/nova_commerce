from datetime import datetime,timezone
import os
import stripe
import random
from fastapi import FastAPI, HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId, utc

from models.products import ProductCreate, ProductUpdate
from database import products_collection,carts_collection,orders_collection,payment_attempts_collection,conversations_collection,conversation_messages_collection
from models.basemodels import  CartItemUpdate, CartItemCreate,CheckoutRequest,OrderCreate,PaymentCreate,OrderStatusUpdate,WhatsAppMessage
from models.products import router as products_router

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

@app.get("/")
def home():
    return {
        "message": "NOVA Commerce API is running"
    }

# get cart

def cart_response(cart):
    return {
        "id": str(cart["_id"]),
        "customer_id": cart["customer_id"],
        "items": cart.get("items", []),
        "total_items": sum(
            item["quantity"]
            for item in cart.get("items", [])
        ),
        "subtotal": sum(
            item["price"] * item["quantity"]
            for item in cart.get("items", [])
        )
    }

@app.get("/cart")
def get_cart(customer_id: str):

    cart = carts_collection.find_one({
        "customer_id": customer_id
    })

    if not cart:
        return {
            "customer_id": customer_id,
            "items": [],
            "total_items": 0,
            "subtotal": 0
        }

    return cart_response(cart)

# add product to cart

@app.post("/cart/items")
def add_to_cart(
    customer_id: str,
    item: CartItemCreate
):

    try:
        product_id = ObjectId(item.product_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    product = products_collection.find_one({
        "_id": product_id
    })

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product["stock"] < item.quantity:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock available"
        )

    cart = carts_collection.find_one({
        "customer_id": customer_id
    })

    if not cart:

        new_item = {
            "product_id": str(product["_id"]),
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "quantity": item.quantity
        }

        result = carts_collection.insert_one({
            "customer_id": customer_id,
            "items": [new_item]
        })

        created_cart = carts_collection.find_one({
            "_id": result.inserted_id
        })

        return cart_response(created_cart)

    existing_item = None

    for cart_item in cart.get("items", []):
        if cart_item["product_id"] == item.product_id:
            existing_item = cart_item
            break

    if existing_item:

        new_quantity = existing_item["quantity"] + item.quantity

        if new_quantity > product["stock"]:
            raise HTTPException(
                status_code=400,
                detail="Not enough stock available"
            )

        carts_collection.update_one(
            {
                "_id": cart["_id"],
                "items.product_id": item.product_id
            },
            {
                "$set": {
                    "items.$.quantity": new_quantity
                }
            }
        )

    else:

        new_item = {
            "product_id": str(product["_id"]),
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "quantity": item.quantity
        }

        carts_collection.update_one(
            {
                "_id": cart["_id"]
            },
            {
                "$push": {
                    "items": new_item
                }
            }
        )

    updated_cart = carts_collection.find_one({
        "_id": cart["_id"]
    })

    return cart_response(updated_cart)


# update quantity of cart items

@app.put("/cart/items/{product_id}")
def update_cart_item(
    product_id: str,
    customer_id: str,
    item: CartItemUpdate
):

    cart = carts_collection.find_one({
        "customer_id": customer_id
    })

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    product = products_collection.find_one({
        "_id": ObjectId(product_id)
    })

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if item.quantity > product["stock"]:
        raise HTTPException(
            status_code=400,
            detail="Not enough stock available"
        )

    result = carts_collection.update_one(
        {
            "_id": cart["_id"],
            "items.product_id": product_id
        },
        {
            "$set": {
                "items.$.quantity": item.quantity
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Product is not in cart"
        )

    updated_cart = carts_collection.find_one({
        "_id": cart["_id"]
    })

    return cart_response(updated_cart)

# Remove Item
@app.delete("/cart/items/{product_id}")
def remove_cart_item(
    product_id: str,
    customer_id: str
):

    cart = carts_collection.find_one({
        "customer_id": customer_id
    })

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    result = carts_collection.update_one(
        {
            "_id": cart["_id"]
        },
        {
            "$pull": {
                "items": {
                    "product_id": product_id
                }
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Product is not in cart"
        )

    updated_cart = carts_collection.find_one({
        "_id": cart["_id"]
    })

    return cart_response(updated_cart)

# Clear Cart
@app.delete("/cart")
def clear_cart(customer_id: str):

    result = carts_collection.delete_one({
        "customer_id": customer_id
    })

    return {
        "message": "Cart cleared successfully"
    }

# valid postcode for now
def validate_postcode(postcode: str) -> bool:

    allowed_postcodes = [
        "54000",
        "54010",
        "54020",
        "54030"
    ]

    return postcode.upper().strip() in allowed_postcodes

# delivery fee calculation
def calculate_delivery_fee(postcode: str) -> float:

    postcode = postcode.upper().strip()

    if postcode == "54000":
        return 29

    if postcode in ["54010", "54020"]:
        return 39

    if postcode == "54030":
        return 49

    return 0

# checkout
@app.post("/checkout/validate")
def validate_checkout(checkout: CheckoutRequest):

    # ----------------------------------------
    # 1. Find customer's cart
    # ----------------------------------------

    cart = carts_collection.find_one({
        "customer_id": checkout.customer_id
    })

    if not cart or not cart.get("items"):
        raise HTTPException(
            status_code=400,
            detail="Cart is empty"
        )

    # ----------------------------------------
    # 2. Validate postcode
    # ----------------------------------------

    if not validate_postcode(checkout.postcode):
        raise HTTPException(
            status_code=400,
            detail="Delivery is not available for this postcode"
        )

    # ----------------------------------------
    # 3. Validate cart products and stock
    # ----------------------------------------

    validated_items = []
    subtotal = 0

    for cart_item in cart["items"]:

        try:
            product_id = ObjectId(
                cart_item["product_id"]
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid product ID in cart"
            )

        product = products_collection.find_one({
            "_id": product_id
        })

        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{cart_item['name']}' is no longer available"
            )

        quantity = cart_item["quantity"]

        # Check stock
        if product["stock"] < quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough stock for "
                    f"'{product['name']}'. "
                    f"Available stock: {product['stock']}"
                )
            )

        # ----------------------------------------
        # Use current database price
        # ----------------------------------------

        unit_price = product["price"]

        line_total = unit_price * quantity

        subtotal += line_total

        validated_items.append({
            "product_id": str(product["_id"]),
            "name": product["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "image": product["image"]
        })

    # ----------------------------------------
    # 4. Calculate delivery fee
    # ----------------------------------------

    delivery_fee = calculate_delivery_fee(
        checkout.postcode
    )

    # ----------------------------------------
    # 5. Calculate final total
    # ----------------------------------------

    total = subtotal + delivery_fee

    # ----------------------------------------
    # 6. Return checkout summary
    # ----------------------------------------

    return {
        "valid": True,

        "customer": {
            "customer_id": checkout.customer_id,
            "name": checkout.name,
            "email": checkout.email,
            "phone": checkout.phone
        },

        "delivery": {
            "address": checkout.address,
            "city": checkout.city,
            "postcode": checkout.postcode.upper().strip(),
            "delivery_fee": delivery_fee
        },

        "items": validated_items,

        "pricing": {
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total
        }
    }

# generate order number
def generate_order_number():
    number =random.randint(100000,999999)
    return f"ORD-{number}"

# Create order
@app.post("/orders")
def create_order(order: OrderCreate):

    # ----------------------------------------
    # 1. Find customer's cart
    # ----------------------------------------

    cart = carts_collection.find_one({
        "customer_id": order.customer_id
    })

    if not cart or not cart.get("items"):
        raise HTTPException(
            status_code=400,
            detail="Cart is empty"
        )

    # ----------------------------------------
    # 2. Validate postcode
    # ----------------------------------------

    if not validate_postcode(order.postcode):
        raise HTTPException(
            status_code=400,
            detail="Delivery is not available for this postcode"
        )

    # ----------------------------------------
    # 3. Validate products and stock
    # ----------------------------------------

    order_items = []
    subtotal = 0

    for cart_item in cart["items"]:

        try:
            product_id = ObjectId(
                cart_item["product_id"]
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid product ID in cart"
            )

        product = products_collection.find_one({
            "_id": product_id
        })

        if not product:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Product '{cart_item['name']}' "
                    "is no longer available"
                )
            )

        quantity = cart_item["quantity"]

        # ----------------------------------------
        # Check stock
        # ----------------------------------------

        if product["stock"] < quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough stock for "
                    f"'{product['name']}'. "
                    f"Available stock: {product['stock']}"
                )
            )

        # ----------------------------------------
        # Use current database price
        # ----------------------------------------

        unit_price = product["price"]

        line_total = unit_price * quantity

        subtotal += line_total

        order_items.append({
            "product_id": str(product["_id"]),
            "name": product["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
            "image": product["image"]
        })

    # ----------------------------------------
    # 4. Calculate delivery fee
    # ----------------------------------------

    delivery_fee = calculate_delivery_fee(
        order.postcode
    )

    # ----------------------------------------
    # 5. Calculate final total
    # ----------------------------------------

    total = subtotal + delivery_fee

    # ----------------------------------------
    # 6. Determine initial order status
    # ----------------------------------------

    if order.payment_method == "online_card":
        order_status = "pending_payment"
        payment_status = "pending"

    else:
        order_status = "confirmed"
        payment_status = "pending"

    # ----------------------------------------
    # 7. Create order document
    # ----------------------------------------

    order_document = {
        "order_number": generate_order_number(),

        "customer": {
            "customer_id": order.customer_id,
            "name": order.name,
            "email": order.email,
            "phone": order.phone
        },

        "items": order_items,

        "delivery": {
            "address": order.address,
            "city": order.city,
            "postcode": order.postcode.upper().strip(),
            "delivery_fee": delivery_fee
        },

        "pricing": {
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total
        },

        "payment": {
            "method": order.payment_method,
            "status": payment_status
        },

        "status": order_status,

        "source": "website",

        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    # ----------------------------------------
    # 8. Save order
    # ----------------------------------------

    result = orders_collection.insert_one(
        order_document
    )

    # ----------------------------------------
    # 9. Reduce product stock
    # ----------------------------------------

    for cart_item in cart["items"]:

        product_id = ObjectId(
            cart_item["product_id"]
        )

        products_collection.update_one(
            {"_id": product_id},
            {
                "$inc": {
                    "stock": -cart_item["quantity"]
                }
            }
        )

    # ----------------------------------------
    # 10. Clear cart
    # ----------------------------------------

    carts_collection.delete_one({
        "customer_id": order.customer_id
    })

    # ----------------------------------------
    # 11. Return order
    # ----------------------------------------

    return {
        "message": "Order created successfully",
        "order_id": str(result.inserted_id),
        "order_number": order_document["order_number"],
        "status": order_status,
        "payment_method": order.payment_method,
        "payment_status": payment_status,
        "items": order_items,
        "pricing": {
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total
        },
        "customer": order_document["customer"],
        "delivery": order_document["delivery"]
    }

# get orders
@app.get("/orders")
def get_orders(customer_id: str | None = None):

    query = {}

    if customer_id:
        query["customer.customer_id"] = customer_id

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
            "delivery": order["delivery"],
            "pricing": order["pricing"],
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

# get order by id
@app.get("/orders/{order_id}")
def get_order(order_id: str):

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

# order status
@app.put("/orders/{order_id}/status")
def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate
):

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

    new_status = status_update.status

    # Prevent confirming an unpaid online-card order
    if (
        new_status == "confirmed"
        and order["payment"]["method"] == "online_card"
        and order["payment"]["status"] != "paid"
    ):
        raise HTTPException(
            status_code=400,
            detail="Online payment must be completed before confirming the order"
        )

    orders_collection.update_one(
        {
            "_id": ObjectId(order_id)
        },
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
        }
    )

    updated_order = orders_collection.find_one({
        "_id": ObjectId(order_id)
    })

    return {
        "message": "Order status updated successfully",
        "order_id": str(updated_order["_id"]),
        "order_number": updated_order["order_number"],
        "status": updated_order["status"],
        "updated_at": updated_order["updated_at"]
    }

# order tracking by id
@app.get("/orders/{order_id}/tracking")
def track_order(order_id: str):

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

        "status": order["status"],

        "payment": {
            "method": order["payment"]["method"],
            "status": order["payment"]["status"]
        },

        "items": order["items"],

        "pricing": order["pricing"],

        "delivery": {
            "address": order["delivery"]["address"],
            "city": order["delivery"]["city"],
            "postcode": order["delivery"]["postcode"],
            "delivery_fee": order["delivery"]["delivery_fee"]
        },

        "created_at": order["created_at"],
        "updated_at": order["updated_at"]
    }


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
