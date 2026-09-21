from fastapi import Depends, HTTPException, APIRouter
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import Optional, List, Annotated
from database import products_collection
from bson import ObjectId

router = APIRouter(
    prefix="/products",
    responses={404: {"description": "Not found"}},
)

PyObjectId = Annotated[str, BeforeValidator(str)]

class Product(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field()
    descritpion: str = Field()
    price: str = Field()
    category: str = Field()
    image: str = Field()
    stock: int = Field(default=0)
    featured: bool = Field(default=False)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ProductCollection(BaseModel):
    products: List[Product]

class ProductCreate(BaseModel):
    name: str = Field()
    descritpion: str = Field()
    price: str = Field()
    category: str = Field()
    image: str = Field()
    stock: int = Field(default=0)
    featured: bool = Field(default=False)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    descritpion: Optional[str] = Field(default=None)
    price: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    image: Optional[str] = Field(default=None)
    stock: Optional[int] = Field(default=None)
    featured: Optional[bool] = Field(default=None)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

@router.post(
    path="/",
    summary="Create a new product",
    description="Create a new product and store it in MongoDB.",
    response_model=Product
)
def create_product(product: ProductCreate):
    product_data = product.model_dump()
    result = products_collection.insert_one(product_data)
    new_product = products_collection.find_one({
        "_id": result.inserted_id
    })

    return new_product

@router.get(
    path="/",
    summary="Get all products",
    description="Get all products from the database.",
    response_model=ProductCollection
)
def get_products():
    return ProductCollection(products=products_collection.find({}))

@router.get(
    path="/{product_id}",
    summary="Get a single product",
    description="Get a product using its MongoDB ObjectId.",
    response_model=Product
)
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

    # print(product)

    return product


@router.put(
    path="/{product_id}",
    summary="Update a product",
    description="Update one or more fields of an existing product.",
    response_model=Product
)
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

    return updated_product

@router.delete(
    path="/{product_id}",
    summary="Delete a product",
    description="Delete a product using its MongoDB ObjectId."
)
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

    return True