"""
MongoDB Database Layer for BuyMeLink
Handles connection, schemas, caching, and analytics
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "buymelink")
MONGODB_MAX_POOL_SIZE = int(os.getenv("MONGODB_MAX_POOL_SIZE", "10"))
MONGODB_MIN_POOL_SIZE = int(os.getenv("MONGODB_MIN_POOL_SIZE", "1"))
MONGODB_CONNECT_TIMEOUT = int(os.getenv("MONGODB_CONNECT_TIMEOUT", "5000"))
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT", "5000"))

# Cache configuration
CACHE_TTL_DAYS = 7  # Products considered fresh for 7 days
EXPIRY_TTL_DAYS = 30  # Auto-delete after 30 days


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class AffiliateLink(BaseModel):
    """Affiliate link for a product on a platform"""
    platform: str
    url: str
    price: str
    commission: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    priority: int = 1
    status: str = "success"
    error_message: Optional[str] = None


class ProductSchema(BaseModel):
    """Product document in MongoDB"""
    name: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    affiliate_links: List[AffiliateLink] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=EXPIRY_TTL_DAYS))

    class Config:
        populate_by_name = True


class SearchSchema(BaseModel):
    """Search query log for analytics"""
    query: str
    product_name: str
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    results_count: int
    source: str  # "cache", "fresh", "partial"
    duration_ms: float
    errors: List[str] = []


class UserSchema(BaseModel):
    """User document for tracking"""
    email: str
    total_searches: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_search_at: Optional[datetime] = None


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class Database:
    """MongoDB connection manager with connection pooling"""

    _instance: Optional['Database'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> AsyncIOMotorDatabase:
        """Initialize MongoDB connection with pooling"""
        if self._client is not None:
            return self._db

        try:
            self._client = AsyncIOMotorClient(
                MONGODB_URL,
                maxPoolSize=MONGODB_MAX_POOL_SIZE,
                minPoolSize=MONGODB_MIN_POOL_SIZE,
                connectTimeoutMS=MONGODB_CONNECT_TIMEOUT,
                serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT,
            )

            # Test connection
            await self._client.admin.command('ping')

            self._db = self._client[MONGODB_DB_NAME]
            logger.info(f"Connected to MongoDB: {MONGODB_DB_NAME}")

            # Create indexes
            await self._create_indexes()

            return self._db

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Products collection indexes
            products = self._db.products
            await products.create_index([("name", TEXT)], name="text_search")
            await products.create_index([("name", ASCENDING)], unique=True, name="unique_name")
            await products.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expires")
            await products.create_index([("updated_at", DESCENDING)], name="updated_desc")
            await products.create_index([("category", ASCENDING)], name="category_idx")

            # Search logs collection indexes
            searches = self._db.search_logs
            await searches.create_index([("timestamp", DESCENDING)], name="timestamp_desc")
            await searches.create_index([("query", TEXT)], name="query_text")
            await searches.create_index([("user_id", ASCENDING)], name="user_idx")

            # Users collection indexes
            users = self._db.users
            await users.create_index([("email", ASCENDING)], unique=True, name="unique_email")

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    async def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")

    def get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    @property
    def products(self) -> AsyncIOMotorCollection:
        """Get products collection"""
        return self.get_db().products

    @property
    def search_logs(self) -> AsyncIOMotorCollection:
        """Get search logs collection"""
        return self.get_db().search_logs

    @property
    def users(self) -> AsyncIOMotorCollection:
        """Get users collection"""
        return self.get_db().users


# Global database instance
db = Database()


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

async def connect_db():
    """Initialize database connection"""
    await db.connect()


async def close_db():
    """Close database connection"""
    await db.close()


# --- Product Functions ---

async def create_product(product_data: dict) -> Optional[str]:
    """
    Create a new product in the database
    Returns the product ID if successful, None otherwise
    """
    try:
        product = ProductSchema(**product_data)
        result = await db.products.insert_one(product.model_dump(by_alias=True))
        logger.info(f"Created product: {product.name} (ID: {result.inserted_id})")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        return None


async def get_product_by_name(name: str) -> Optional[dict]:
    """
    Get product from cache by name
    Returns product dict if found and not expired, None otherwise
    """
    try:
        # Check if product exists and not expired
        product = await db.products.find_one({
            "name": name,
            "expires_at": {"$gt": datetime.utcnow()}
        })

        if product:
            logger.info(f"Cache HIT for product: {name}")
            # Update access time
            await db.products.update_one(
                {"_id": product["_id"]},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            return product
        else:
            logger.info(f"Cache MISS for product: {name}")
            return None

    except Exception as e:
        logger.error(f"Error fetching product by name: {e}")
        return None


async def update_affiliate_links(product_id: str, links: List[dict]) -> bool:
    """
    Update affiliate links for a product
    Returns True if successful
    """
    try:
        affiliate_links = [AffiliateLink(**link) for link in links]
        result = await db.products.update_one(
            {"_id": product_id},
            {
                "$set": {
                    "affiliate_links": [link.model_dump() for link in affiliate_links],
                    "updated_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(days=EXPIRY_TTL_DAYS)
                }
            }
        )
        success = result.modified_count > 0
        if success:
            logger.info(f"Updated affiliate links for product ID: {product_id}")
        return success
    except Exception as e:
        logger.error(f"Error updating affiliate links: {e}")
        return False


async def update_product_full(product_id: str, product_data: dict) -> bool:
    """
    Update entire product document
    """
    try:
        product_data["updated_at"] = datetime.utcnow()
        product_data["expires_at"] = datetime.utcnow() + timedelta(days=EXPIRY_TTL_DAYS)

        result = await db.products.update_one(
            {"_id": product_id},
            {"$set": product_data}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        return False


async def upsert_product(product_data: dict) -> Optional[str]:
    """
    Insert or update product by name (upsert)
    Returns product ID
    """
    try:
        name = product_data.get("name")
        if not name:
            return None

        product_data["updated_at"] = datetime.utcnow()
        product_data["expires_at"] = datetime.utcnow() + timedelta(days=EXPIRY_TTL_DAYS)

        result = await db.products.update_one(
            {"name": name},
            {"$set": product_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True
        )

        if result.upserted_id:
            logger.info(f"Created new product: {name} (ID: {result.upserted_id})")
            return str(result.upserted_id)
        else:
            logger.info(f"Updated existing product: {name}")
            # Get the ID
            product = await db.products.find_one({"name": name})
            return str(product["_id"]) if product else None

    except Exception as e:
        logger.error(f"Error upserting product: {e}")
        return None


async def delete_expired_products() -> int:
    """
    Delete products older than EXPIRY_TTL_DAYS
    Returns count of deleted products
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=EXPIRY_TTL_DAYS)
        result = await db.products.delete_many({
            "updated_at": {"$lt": cutoff_date}
        })
        logger.info(f"Deleted {result.deleted_count} expired products")
        return result.deleted_count
    except Exception as e:
        logger.error(f"Error deleting expired products: {e}")
        return 0


# --- Search Logging Functions ---

async def log_search_query(
    query: str,
    product_name: str,
    results_count: int,
    source: str,
    duration_ms: float,
    user_id: Optional[str] = None,
    errors: Optional[List[str]] = None
) -> Optional[str]:
    """
    Log a search query for analytics
    Returns log ID if successful
    """
    try:
        search_log = SearchSchema(
            query=query,
            product_name=product_name,
            user_id=user_id,
            results_count=results_count,
            source=source,
            duration_ms=duration_ms,
            errors=errors or []
        )

        result = await db.search_logs.insert_one(search_log.model_dump(by_alias=True))

        # Update user search count if user_id provided
        if user_id:
            await db.users.update_one(
                {"email": user_id},
                {
                    "$inc": {"total_searches": 1},
                    "$set": {"last_search_at": datetime.utcnow()},
                    "$setOnInsert": {"email": user_id, "created_at": datetime.utcnow()}
                },
                upsert=True
            )

        logger.info(f"Logged search: '{query}' -> {product_name} (source: {source})")
        return str(result.inserted_id)

    except Exception as e:
        logger.error(f"Error logging search query: {e}")
        return None


async def get_search_stats() -> Dict[str, Any]:
    """
    Get search analytics statistics
    """
    try:
        # Total searches
        total_searches = await db.search_logs.count_documents({})

        # Searches by source
        pipeline_source = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}}
        ]
        source_stats = await db.search_logs.aggregate(pipeline_source).to_list(length=10)

        # Popular products (most searched)
        pipeline_popular = [
            {"$group": {"_id": "$product_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        popular_products = await db.search_logs.aggregate(pipeline_popular).to_list(length=10)

        # Recent searches (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_searches = await db.search_logs.count_documents({
            "timestamp": {"$gte": day_ago}
        })

        # Average response time
        pipeline_avg = [
            {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_ms"}}}
        ]
        avg_result = await db.search_logs.aggregate(pipeline_avg).to_list(length=1)
        avg_duration = avg_result[0]["avg_duration"] if avg_result else 0

        return {
            "total_searches": total_searches,
            "recent_searches_24h": recent_searches,
            "by_source": {item["_id"]: item["count"] for item in source_stats},
            "popular_products": [
                {"product": item["_id"], "search_count": item["count"]}
                for item in popular_products
            ],
            "avg_response_time_ms": round(avg_duration, 2)
        }

    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        return {
            "total_searches": 0,
            "recent_searches_24h": 0,
            "by_source": {},
            "popular_products": [],
            "avg_response_time_ms": 0
        }


async def get_recent_searches(limit: int = 20, user_id: Optional[str] = None) -> List[dict]:
    """
    Get recent search queries
    """
    try:
        query_filter = {}
        if user_id:
            query_filter["user_id"] = user_id

        cursor = db.search_logs.find(query_filter).sort("timestamp", -1).limit(limit)
        searches = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for search in searches:
            search["_id"] = str(search["_id"])

        return searches

    except Exception as e:
        logger.error(f"Error getting recent searches: {e}")
        return []


# --- User Functions ---

async def get_or_create_user(email: str) -> dict:
    """
    Get user by email or create if not exists
    """
    try:
        user = await db.users.find_one({"email": email})
        if not user:
            user = UserSchema(email=email)
            result = await db.users.insert_one(user.model_dump(by_alias=True))
            user["_id"] = str(result.inserted_id)
        else:
            user["_id"] = str(user["_id"])
        return user
    except Exception as e:
        logger.error(f"Error getting/creating user: {e}")
        return {"email": email, "total_searches": 0}


async def get_user_stats(email: str) -> dict:
    """
    Get statistics for a specific user
    """
    try:
        user = await db.users.find_one({"email": email})
        if not user:
            return {"email": email, "total_searches": 0, "searches": []}

        searches = await get_recent_searches(limit=50, user_id=email)

        return {
            "email": email,
            "total_searches": user.get("total_searches", 0),
            "created_at": user.get("created_at"),
            "last_search_at": user.get("last_search_at"),
            "recent_searches": searches
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {"email": email, "total_searches": 0, "searches": []}