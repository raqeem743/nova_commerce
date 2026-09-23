import stripe
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import products
from routers import cart
from routers import  checkout
from routers import orders
from routers import payments
from routers import  admin
from routers import whatsapp

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

@app.get("/")
def home():
    return {
        "message": "NOVA Commerce API is running"
    }

app.include_router(products.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(admin.router)
app.include_router(whatsapp.router)




