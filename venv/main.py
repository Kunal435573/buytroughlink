from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import urllib.parse
import logging
import time
import json

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BuyMeLink API", version="1.0.0")

# Allow CORS for web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class ProductLink(BaseModel):
    platform: str
    url: str
    price: str
    commission: str
    priority: int
    status: Literal["success", "failed", "timeout", "error"] = "success"
    error_message: Optional[str] = None

class SearchResponse(BaseModel):
    product_name: str
    links: List[ProductLink]
    search_time: datetime = Field(default_factory=datetime.utcnow)
    source: Literal["web", "api", "cache"] = "web"
    partial: bool = False
    errors: List[str] = []

# Common headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

DEFAULT_TIMEOUT = 10

def log_request(query: str, platform: str, status: str, error: str = None, duration: float = None):
    """Log search request details."""
    log_data = {
        "query": query,
        "platform": platform,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if error:
        log_data["error"] = error
    if duration:
        log_data["duration_ms"] = round(duration * 1000, 2)

    if status == "success":
        logger.info(f"Search request: {json.dumps(log_data)}")
    elif status == "timeout":
        logger.warning(f"Search timeout: {json.dumps(log_data)}")
    else:
        logger.error(f"Search failed: {json.dumps(log_data)}")

def safe_request(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response | None:
    """Make a safe HTTP request with error handling."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Request timed out after {timeout}s")
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Connection error: {str(e)}")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Request failed: {str(e)}")

def create_fallback_result(platform: str, query: str, url: str, commission: str, priority: int,
                          error_message: str = None, status: str = "failed") -> dict:
    """Create a fallback result when scraping fails."""
    return {
        "platform": platform,
        "url": url,
        "price": "N/A",
        "commission": commission,
        "priority": priority,
        "status": status,
        "error_message": error_message
    }

def search_amazon(query: str) -> dict:
    """Scrape Amazon.in search results for the first product."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    start_time = time.time()
    platform = "Amazon"

    try:
        response = safe_request(url)
        if not response:
            error_msg = "No response received"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "3-5%", 1, error_msg)

        soup = BeautifulSoup(response.text, "lxml")

        # Find first product result
        product = soup.select_one("div[data-component-type='s-search-result']")
        if not product:
            error_msg = "No products found in search results"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "3-5%", 1, error_msg)

        # Extract product URL
        link_elem = product.select_one("h2 a")
        product_url = "https://www.amazon.in" + link_elem["href"] if link_elem and link_elem.get("href") else url

        # Extract price
        price_elem = product.select_one(".a-price-whole")
        price_fraction = product.select_one(".a-price-fraction")
        price = "N/A"
        if price_elem:
            price = "₹" + price_elem.get_text(strip=True).replace(",", "")
            if price_fraction:
                price += "." + price_fraction.get_text(strip=True)

        duration = time.time() - start_time
        log_request(query, platform, "success", duration=duration)

        return {
            "platform": platform,
            "url": product_url,
            "price": price,
            "commission": "3-5%",
            "priority": 1,
            "status": "success",
            "error_message": None
        }

    except TimeoutError as e:
        duration = time.time() - start_time
        log_request(query, platform, "timeout", str(e), duration)
        return create_fallback_result(platform, query, url, "3-5%", 1, str(e), "timeout")
    except ConnectionError as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "3-5%", 1, str(e), "error")
    except Exception as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "3-5%", 1, str(e), "error")

def search_flipkart(query: str) -> dict:
    """Scrape Flipkart search results for the first product."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.flipkart.com/search?q={encoded_query}"
    start_time = time.time()
    platform = "Flipkart"

    try:
        response = safe_request(url)
        if not response:
            error_msg = "No response received"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "4-6%", 2, error_msg)

        soup = BeautifulSoup(response.text, "lxml")

        # Find first product result
        product = soup.select_one("div[data-id]") or soup.select_one("._1AtVbE")
        if not product:
            error_msg = "No products found in search results"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "4-6%", 2, error_msg)

        # Extract product URL
        link_elem = product.select_one("a._1fQZEK") or product.select_one("a.s1Q9rs") or product.select_one("a._2rpwqI")
        product_url = "https://www.flipkart.com" + link_elem["href"] if link_elem and link_elem.get("href") else url

        # Extract price
        price_elem = product.select_one("div._30jeq3") or product.select_one("div._1_WHN1")
        price = price_elem.get_text(strip=True) if price_elem else "N/A"

        duration = time.time() - start_time
        log_request(query, platform, "success", duration=duration)

        return {
            "platform": platform,
            "url": product_url,
            "price": price,
            "commission": "4-6%",
            "priority": 2,
            "status": "success",
            "error_message": None
        }

    except TimeoutError as e:
        duration = time.time() - start_time
        log_request(query, platform, "timeout", str(e), duration)
        return create_fallback_result(platform, query, url, "4-6%", 2, str(e), "timeout")
    except ConnectionError as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "4-6%", 2, str(e), "error")
    except Exception as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "4-6%", 2, str(e), "error")

def search_meesho(query: str) -> dict:
    """Scrape Meesho search results for the first product."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.meesho.com/search?q={encoded_query}"
    start_time = time.time()
    platform = "Meesho"

    try:
        response = safe_request(url)
        if not response:
            error_msg = "No response received"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "5-10%", 3, error_msg)

        soup = BeautifulSoup(response.text, "lxml")

        # Find first product result
        product = soup.select_one("div[class*='ProductList__GridCol']") or soup.select_one("div.NewProductCardstyled__Wrapper-sc-1xql6p-0")
        if not product:
            error_msg = "No products found in search results"
            log_request(query, platform, "failed", error_msg, time.time() - start_time)
            return create_fallback_result(platform, query, url, "5-10%", 3, error_msg)

        # Extract product URL
        link_elem = product.select_one("a[href*='/product/']") or product.select_one("a")
        product_url = "https://www.meesho.com" + link_elem["href"] if link_elem and link_elem.get("href") else url

        # Extract price
        price_elem = product.select_one("h4[class*='Price']") or product.select_one("div[class*='Price']") or product.select_one("span[class*='Price']")
        price = price_elem.get_text(strip=True) if price_elem else "N/A"

        duration = time.time() - start_time
        log_request(query, platform, "success", duration=duration)

        return {
            "platform": platform,
            "url": product_url,
            "price": price,
            "commission": "5-10%",
            "priority": 3,
            "status": "success",
            "error_message": None
        }

    except TimeoutError as e:
        duration = time.time() - start_time
        log_request(query, platform, "timeout", str(e), duration)
        return create_fallback_result(platform, query, url, "5-10%", 3, str(e), "timeout")
    except ConnectionError as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "5-10%", 3, str(e), "error")
    except Exception as e:
        duration = time.time() - start_time
        log_request(query, platform, "error", str(e), duration)
        return create_fallback_result(platform, query, url, "5-10%", 3, str(e), "error")

@app.get("/search", response_model=SearchResponse)
async def search_product(
    query: str = Query(..., min_length=1, max_length=200, description="Product search query")
):
    """Search product on affiliate platforms"""
    overall_start = time.time()
    errors = []
    partial = False

    logger.info(f"Starting search for query: '{query}'")

    # Search all platforms with individual error handling
    try:
        amazon_result = search_amazon(query)
        if amazon_result.get("status") != "success":
            partial = True
            if amazon_result.get("error_message"):
                errors.append(f"Amazon: {amazon_result['error_message']}")
    except Exception as e:
        partial = True
        errors.append(f"Amazon: {str(e)}")
        amazon_result = create_fallback_result("Amazon", query, f"https://www.amazon.in/s?k={urllib.parse.quote_plus(query)}", "3-5%", 1, str(e), "error")

    try:
        flipkart_result = search_flipkart(query)
        if flipkart_result.get("status") != "success":
            partial = True
            if flipkart_result.get("error_message"):
                errors.append(f"Flipkart: {flipkart_result['error_message']}")
    except Exception as e:
        partial = True
        errors.append(f"Flipkart: {str(e)}")
        flipkart_result = create_fallback_result("Flipkart", query, f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(query)}", "4-6%", 2, str(e), "error")

    try:
        meesho_result = search_meesho(query)
        if meesho_result.get("status") != "success":
            partial = True
            if meesho_result.get("error_message"):
                errors.append(f"Meesho: {meesho_result['error_message']}")
    except Exception as e:
        partial = True
        errors.append(f"Meesho: {str(e)}")
        meesho_result = create_fallback_result("Meesho", query, f"https://www.meesho.com/search?q={urllib.parse.quote_plus(query)}", "5-10%", 3, str(e), "error")

    total_duration = time.time() - overall_start

    logger.info(f"Search completed for query: '{query}' in {total_duration:.2f}s | partial={partial} | errors={len(errors)}")

    return SearchResponse(
        product_name=query,
        links=[
            ProductLink(**amazon_result),
            ProductLink(**flipkart_result),
            ProductLink(**meesho_result),
        ],
        search_time=datetime.utcnow(),
        source="web",
        partial=partial,
        errors=errors
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)