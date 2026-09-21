from fastapi import  HTTPException,APIRouter,Request
from database import orders_collection,products_collection
from bson import ObjectId
import os

router=APIRouter(
    # prefix="/get_admin_stats",
    # tags=["Get_admin_stats"]
)

# admin stats panel
@router.get("/")
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
@router.get("/admin/orders")
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
@router.get("/admin/orders/{order_id}")
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
@router.get("/admin/products/low-stock")
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
