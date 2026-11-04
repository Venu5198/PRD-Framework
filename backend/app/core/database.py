import logging
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_mock: bool = False

    async def connect(self):
        try:
            logger.info(f"Probing MongoDB connection at {settings.MONGODB_URI}...")
            real_client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=500,
                connectTimeoutMS=500
            )
            await asyncio.wait_for(real_client.admin.command('ping'), timeout=0.6)
            self.client = real_client
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.is_mock = False
            logger.info(f"Connected to live MongoDB database: {settings.MONGODB_DB_NAME}")
            
            # Initialize indexes
            from app.db.indexes import initialize_database_indexes
            await initialize_database_indexes(self.db)
        except Exception as e:
            logger.info(f"Using in-memory AsyncMongoMockClient database ({e}).")
            from mongomock_motor import AsyncMongoMockClient
            self.client = AsyncMongoMockClient()
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.is_mock = True
            try:
                from app.db.indexes import initialize_database_indexes
                await initialize_database_indexes(self.db)
            except Exception:
                pass

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection.")

db_manager = DatabaseManager()

def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database not initialized. Please call connect() first.")
    return db_manager.db
