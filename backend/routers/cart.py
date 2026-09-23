from fastapi import HTTPException, APIRouter
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from database import products_collection, carts_collection
from bson import ObjectId
from typing import Annotated, Optional, List

router = APIRouter(
    prefix="/cart",
    responses={404: {"description": "Not found"}},
)

PyObjectId = Annotated[str, BeforeValidator(str)]

# --- NEW SCHEMAS FOR SERIALIZATION ---
class CartItem(BaseModel):
    # product_id: str
    # name: str
    # price: float
    # image: str
    # quantity: int = Field(ge=0)
        product_id: Optional[PyObjectId] = Field(alias="_id", default=None)
        name: str = Field()
        # description: Optional[str] = Field(default=None)  # Fixed default
        price: float = Field()
        # category: str = Field()
        image: str = Field()
        # stock: int = Field(default=0)
        # featured: bool = Field(default=False)
        model_config = ConfigDict(
            populate_by_name=True,
            arbitrary_types_allowed=True,
        )

class CartResponse(BaseModel):
    id: str
    customer_id: str
    items: List[CartItem] = []
    total_items: int = 0
    subtotal: float = 0.0

class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0)

class CartItemCreate(BaseModel):
    product_id: PyObjectId = Field(alias="_id") # Required for identifying target product
    quantity: int = Field(default=1, ge=1)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Formatting helper function
def cart_response(cart):
    return {
        "id": str(cart["_id"]),
        "customer_id": cart["customer_id"],
        "items": cart.get("items", []),
        "total_items": sum(item["quantity"] for item in cart.get("items", [])),
        "subtotal": sum(item["price"] * item["quantity"] for item in cart.get("items", []))
    }

@router.get(
    path="/",
    summary="Get a cart",
    description="Get a cart and store it in mongodb",
    response_model=CartResponse  # Fixed response model mapping
)
def get_cart(customer_id: str):
    cart = carts_collection.find_one({"customer_id": customer_id})

    if not cart:
        return {
            "id": "",
            "customer_id": customer_id,
            "items": [],
            "total_items": 0,
            "subtotal": 0.0
        }

    return cart_response(cart)

@router.post(
    path="/",
    summary="Add product to cart",
    description="Add an item to the cart and return the full cart view.",
    response_model=CartResponse  # Fixed response model mapping
)
def add_to_cart(customer_id: str, item: CartItemCreate):
    try:
        product_id = ObjectId(item.product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = products_collection.find_one({"_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product["stock"] < item.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")

    cart = carts_collection.find_one({"customer_id": customer_id})

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

        created_cart = carts_collection.find_one({"_id": result.inserted_id})
        return cart_response(created_cart)

    existing_item = None
    for cart_item in cart.get("items", []):
        if cart_item["product_id"] == item.product_id:
            existing_item = cart_item
            break

    if existing_item:
        new_quantity = existing_item["quantity"] + item.quantity
        if new_quantity > product["stock"]:
            raise HTTPException(status_code=400, detail="Not enough stock available")

        carts_collection.update_one(
            {"_id": cart["_id"], "items.product_id": item.product_id},
            {"$set": {"items.$.quantity": new_quantity}}
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
            {"_id": cart["_id"]},
            {"$push": {"items": new_item}}
        )

    updated_cart = carts_collection.find_one({"_id": cart["_id"]})
    return cart_response(updated_cart)

@router.put(
    path="/{product_id}",
    summary="Update cart item quantity",
    description="Update the quantity of a specific item in the cart.",
    response_model=CartResponse  # Fixed response model mapping
)
def update_cart_item(product_id: str, customer_id: str, item: CartItemUpdate):
    cart = carts_collection.find_one({"customer_id": customer_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if item.quantity > product["stock"]:
        raise HTTPException(status_code=400, detail="Not enough stock available")

    result = carts_collection.update_one(
        {"_id": cart["_id"], "items.product_id": product_id},
        {"$set": {"items.$.quantity": item.quantity}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product is not in cart")

    updated_cart = carts_collection.find_one({"_id": cart["_id"]})
    return cart_response(updated_cart)

@router.delete(
    path="/{product_id}",
    summary="remove cart item",
    description="remove cart item by id",
    response_model=CartResponse # Added to give immediate cart update context to frontend
)
def remove_cart_item(product_id: str, customer_id: str):
    cart = carts_collection.find_one({"customer_id": customer_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    result = carts_collection.update_one(
        {"_id": cart["_id"]},
        {"$pull": {"items": {"product_id": product_id}}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product is not in cart")

    updated_cart = carts_collection.find_one({"_id": cart["_id"]})
    return cart_response(updated_cart)

@router.delete(
    path="/",
    summary="clear cart",
    description="clear the whole cart",
)
def clear_cart(customer_id: str):
    carts_collection.delete_one({"customer_id": customer_id})
    return {"message": "Cart cleared successfully"}
