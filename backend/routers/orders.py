from datetime import datetime, timezone
from fastapi import  HTTPException,APIRouter
from pydantic import BaseModel, ConfigDict, Field
import random
from typing import Literal, Optional
from routers.cart import PyObjectId
from routers.checkout import calculate_delivery_fee, validate_postcode
from database import products_collection,carts_collection,orders_collection
from bson import ObjectId

router=APIRouter(
    prefix="/orders",
    responses={404: {"description": "Not found"}},
)

class OrderCreate(BaseModel):
    # customer_id: str
    # name: str
    # email: str
    # phone: str
    # address: str
    # city: str
    # postcode: str
    # payment_method: Literal[
    #     "online_card",
    #     "cash_on_delivery",
    #     "card_on_delivery"
    # ]
        customer_id: Optional[PyObjectId] = Field(alias="_id", default=None)
        name: str = Field()
        email:str =Field()
        phone:str =Field()
        address:str =Field()
        city:str =Field()
        postcode:str =Field()
        payment_method: Literal[
                "online_card",
                "cash_on_delivery",
                "card_on_delivery"
            ]
        model_config = ConfigDict(
            populate_by_name=True,
            arbitrary_types_allowed=True,
        )

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


# generate order number
def generate_order_number():
    number =random.randint(100000,999999)
    return f"ORD-{number}"

# Create order
@router.post(path="/",
    summary="Create a new order",
    description="Create a new order in mongodb",
    response_model=OrderCreate
    )
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
@router.get(path="/",
    summary="get orders",
    description="Get all the orders",
    response_model=OrderCreate)

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
@router.get(
    path="/{order_id}",
    summary="Get order by id",
    description="get order by id",
    response_model=OrderCreate
    )

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
@router.put(path="/status/{order_id}",
    summary="update order status",
    description="Update order status.",
    response_model=OrderStatusUpdate)
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
@router.get(path="/{order_id}/track",
    summary="Track order",
    description="Track order by id ",
    response_model=OrderStatusUpdate)
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