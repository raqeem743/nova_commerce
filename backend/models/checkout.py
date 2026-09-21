from fastapi import APIRouter,HTTPException
from pydantic import BaseModel, EmailStr
from database import products_collection,carts_collection
from bson import ObjectId

router =APIRouter()

class CheckoutRequest(BaseModel):
    customer_id: str
    name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    postcode: str

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

# validate checkout
@router.post("/checkout/validate")
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