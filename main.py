from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv
import socket

load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="BuyMeLink API",
    version="1.0.0",
    description="Affiliate Link Finder"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup/Shutdown
@app.on_event("startup")
async def startup():
    logger.info("🚀 BuyMeLink Backend Starting...")

@app.on_event("shutdown")
async def shutdown():
    logger.info("❌ BuyMeLink Backend Shutting Down...")

# Endpoints
@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {
        "message": "BuyMeLink Backend Running! 🚀",
        "version": "1.0.0",
        "status": "success"
    }

@app.get("/search")
async def search_product(query: str = Query(..., min_length=2, max_length=100)):
    """Search affiliate links for product"""
    start_time = time.time()

    logger.info(f"Search query: {query}")

    if not query:
        logger.warning("Empty query received")
        raise HTTPException(status_code=400, detail="Query required")

    try:
        # Search all platforms
        links = []

        # Amazon
        try:
            amazon = search_amazon(query)
            if amazon:
                links.append(amazon)
        except Exception as e:
            logger.error(f"Amazon search failed: {e}")

        # Flipkart
        try:
            flipkart = search_flipkart(query)
            if flipkart:
                links.append(flipkart)
        except Exception as e:
            logger.error(f"Flipkart search failed: {e}")

        # Meesho
        try:
            meesho = search_meesho(query)
            if meesho:
                links.append(meesho)
        except Exception as e:
            logger.error(f"Meesho search failed: {e}")

        duration = time.time() - start_time
        logger.info(f"Search completed for '{query}' in {duration:.2f}s - Found {len(links)} links")

        return {
            "product_name": query,
            "links": links,
            "source": "fresh",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "duration_seconds": round(duration, 2)
        }

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "product_name": query,
            "links": [],
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/products/trending")
async def get_trending():
    """Get trending products"""
    logger.info("Trending products endpoint called")
    return {
        "trending": [
            "iPhone 15 Pro",
            "MacBook Pro M3",
            "Samsung Galaxy S24",
            "iPad Pro",
            "AirPods Pro",
            "Apple Watch",
            "Sony WH-1000XM5",
            "DJI Mini 4 Pro"
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }

@app.get("/analytics/stats")
async def get_stats():
    """Get analytics statistics"""
    logger.info("Analytics endpoint called")
    return {
        "total_searches": 0,
        "cache_hit_rate": "0%",
        "popular_products": [],
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }

# Search Functions
def search_amazon(query: str) -> Optional[Dict]:
    """Search Amazon for product"""
    try:
        url = f"https://amazon.in/s?k={query}"
        return {
            "platform": "Amazon",
            "url": url,
            "commission": "3-5%",
            "priority": 1,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Amazon search error: {e}")
        return None

def search_flipkart(query: str) -> Optional[Dict]:
    """Search Flipkart for product"""
    try:
        url = f"https://www.flipkart.com/search?q={query}"
        return {
            "platform": "Flipkart",
            "url": url,
            "commission": "4-6%",
            "priority": 2,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Flipkart search error: {e}")
        return None

def search_meesho(query: str) -> Optional[Dict]:
    """Search Meesho for product"""
    try:
        url = f"https://www.meesho.com/search?q={query}"
        return {
            "platform": "Meesho",
            "url": url,
            "commission": "5-10%",
            "priority": 3,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Meesho search error: {e}")
        return None

# Find available port
def find_available_port(start_port=8000, max_attempts=10):
    """Find available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port

if __name__ == "__main__":
    port = find_available_port(8000)
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)