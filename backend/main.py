import stripe
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import products
from models.cart import router as cart_router
from models.checkout import router as checkout_router
from models.orders import router as orders_router
from models.payments import router as payments_router
from models.admin import router as admin_router
from models.whatsapp import router as whatsapp_router

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

app.include_router(products.router)
app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(whatsapp_router)

@app.get("/")
def home():
    return {
        "message": "NOVA Commerce API is running"
    }


