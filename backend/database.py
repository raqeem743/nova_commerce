import os

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "nova_commerce")


if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the .env file")


client = MongoClient(MONGO_URI)

db = client[DATABASE_NAME]

products_collection = db["products"]
carts_collection =db["cart"]
orders_collection=db["orders"]
payment_attempts_collection = db["payment_attempts"]
conversations_collection = db["conversations"]
conversation_messages_collection = db["conversation_messages"]