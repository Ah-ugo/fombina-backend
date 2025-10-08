from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "fombina_tower")

# Global MongoDB client
client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB database"""
    global client, database
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        database = client[DATABASE_NAME]
        # Test connection
        await client.admin.command("ping")
        print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


def get_database():
    """Get database instance"""
    return database


# Collection helpers
def get_spaces_collection():
    return database.spaces


def get_bookings_collection():
    return database.bookings


def get_transactions_collection():
    return database.transactions


def get_gallery_collection():
    return database.gallery


def get_timeline_collection():
    return database.timeline


def get_messages_collection():
    return database.messages


def get_admins_collection():
    return database.admins
