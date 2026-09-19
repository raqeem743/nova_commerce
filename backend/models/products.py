from fastapi import FastAPI, HTTPException,APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from database import products_collection
from bson import ObjectId, utc

app =FastAPI()

router =APIRouter()

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float = Field(gt=0)
    category: str
    image: str
    stock: int = Field(default=0, ge=0)
    featured: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    image: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)
    featured: Optional[bool] = None

def product_response(product):
    return {
        "id": str(product["_id"]),
        "name": product["name"],
        "description": product["description"],
        "price": product["price"],
        "category": product["category"],
        "image": product["image"],
        "stock": product["stock"],
        "featured": product["featured"]
    }

# --------------------------------------------------
# Create product
# --------------------------------------------------
@router.post("/products")
def create_product(product: ProductCreate):

    product_data = product.model_dump()

    result = products_collection.insert_one(product_data)

    created_product = products_collection.find_one({
        "_id": result.inserted_id
    })

    return product_response(created_product)


# --------------------------------------------------
# Get all products
# --------------------------------------------------

@router.get("/products")
def get_products():
    products = products_collection.find()

    return [
        product_response(product)
        for product in products
    ]

# --------------------------------------------------
# Get single product
# --------------------------------------------------

@router.get("/products/{product_id}")
def get_product(product_id: str):

    try:
        object_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    product = products_collection.find_one({
        "_id": object_id
    })

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product_response(product)


# --------------------------------------------------
# Update product
# --------------------------------------------------

@router.put("/products/{product_id}")
def update_product(
    product_id: str,
    product: ProductUpdate
):

    try:
        object_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    update_data = {
        key: value
        for key, value in product.model_dump().items()
        if value is not None
    }

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    result = products_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    updated_product = products_collection.find_one({
        "_id": object_id
    })

    return product_response(updated_product)


# --------------------------------------------------
# Delete product
# --------------------------------------------------

@router.delete("/products/{product_id}")
def delete_product(product_id: str):

    try:
        object_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID"
        )

    result = products_collection.delete_one({
        "_id": object_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "message": "Product deleted successfully"
    }
