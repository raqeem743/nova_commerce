from fastapi import  HTTPException,APIRouter
from pydantic import BaseModel, Field
from database import products_collection,carts_collection
from bson import ObjectId, utc

router =APIRouter()

class CartItemUpdate(BaseModel):
    quantity:int =Field(ge=0)

class CartItemCreate(BaseModel):
    product_id:str
    quantity:int =Field(default=0,ge=0)

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

@router.get("/cart")
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

@router.post("/cart/items")
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

@router.put("/cart/items/{product_id}")
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
@router.delete("/cart/items/{product_id}")
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
@router.delete("/cart")
def clear_cart(customer_id: str):

    result = carts_collection.delete_one({
        "customer_id": customer_id
    })

    return {
        "message": "Cart cleared successfully"
    }