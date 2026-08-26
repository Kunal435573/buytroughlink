#!/usr/bin/env python
"""
BuyMeLink Instagram DM Bot
Listens to Instagram DMs, extracts product names, fetches affiliate links from FastAPI backend,
adds bot owner's affiliate IDs, and replies to users.
"""
import os
import re
import time
import json
import logging
import schedule
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

import config

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE
# ============================================================================
cl = Client()
processed_message_ids = set()


# ============================================================================
# INSTAGRAM CLIENT SETUP
# ============================================================================

def setup_client() -> bool:
    """Initialize Instagram client with session persistence"""
    try:
        if os.path.exists(config.SESSION_FILE):
            cl.load_settings(config.SESSION_FILE)
            logger.info("Loaded existing session")

        cl.set_uuids(config.INSTAGRAM_USERNAME)
        return True
    except Exception as e:
        logger.error(f"Failed to setup client: {e}")
        return False


def login() -> bool:
    """Login to Instagram"""
    try:
        logger.info(f"Logging in as {config.INSTAGRAM_USERNAME}...")
        cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
        cl.dump_settings(config.SESSION_FILE)
        logger.info("✅ Login successful")
        return True
    except LoginRequired:
        logger.error("Login required - session expired")
        try:
            cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
            cl.dump_settings(config.SESSION_FILE)
            return True
        except Exception as e:
            logger.error(f"Re-login failed: {e}")
            return False
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False


# ============================================================================
# PRODUCT EXTRACTION FROM REEL
# ============================================================================

def extract_reel_id(url: str) -> Optional[str]:
    """Extract reel/media ID from Instagram URL"""
    patterns = [
        r"instagram\.com/reel/([^/?#&]+)",
        r"instagram\.com/p/([^/?#&]+)",
        r"instagram\.com/tv/([^/?#&]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_product_from_reel(reel_id: str) -> Optional[str]:
    """Get reel info and extract product name from caption"""
    try:
        media = cl.media_info(reel_id)
        caption = media.caption_text or ""

        if not caption:
            logger.warning(f"Reel {reel_id} has no caption")
            return None

        logger.info(f"Reel caption: {caption[:200]}...")

        product_name = clean_product_name(caption)
        return product_name

    except ClientError as e:
        logger.error(f"Instagram API error getting reel: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting product from reel: {e}")
        return None


def clean_product_name(text: str) -> Optional[str]:
    """Clean and extract product name from text"""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[@#]\w+', '', text)
    text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', text)

    words = text.split()
    stop_words = [
        "best", "top", "review", "unboxing", "vs", "comparison",
        "cheap", "budget", "premium", "pro", "max", "plus",
        "new", "latest", "2024", "2025", "buy", "price", "india",
        "online", "deal", "offer", "discount", "sale",
        "₹", "rs", "rupees", "dollar", "$"
    ]

    filtered = [w for w in words if len(w) > 2 and w.lower() not in stop_words]

    if not filtered:
        return None

    product = " ".join(filtered[:7])
    product = re.sub(r'[^\w\s\-]', '', product)
    product = re.sub(r'\s+', ' ', product).strip()

    return product if product else None


def extract_product_from_message(message_text: str) -> Optional[str]:
    """Extract product name from direct message text"""
    text = message_text.strip()

    reel_id = extract_reel_id(text)
    if reel_id:
        logger.info(f"Found reel ID: {reel_id}")
        return extract_product_from_reel(reel_id)

    product = clean_product_name(text)
    return product


# ============================================================================
# FASTAPI BACKEND INTEGRATION
# ============================================================================

def search_affiliate_links(product_name: str) -> Optional[List[Dict]]:
    """Call FastAPI backend to search for affiliate links"""
    try:
        url = f"{config.API_BASE}/search"
        params = {"query": product_name}

        logger.info(f"Calling API: {url}?query={product_name}")

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        links = data.get("links", [])

        logger.info(f"API returned {len(links)} links")
        return links

    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to API backend")
        return None
    except Exception as e:
        logger.error(f"API error: {e}")
        return None


def add_affiliate_tags(links: List[Dict], affiliate_tags: Dict[str, str]) -> List[Dict]:
    """Add bot owner's affiliate tags to links"""
    tagged_links = []

    for link in links:
        platform = link.get("platform", "").lower()
        url = link.get("url", "")

        if not url:
            tagged_links.append(link)
            continue

        tagged_url = url

        if platform == "amazon":
            tag = affiliate_tags.get("amazon", "")
            if tag and "tag=" not in url:
                separator = "&" if "?" in url else "?"
                tagged_url = f"{url}{separator}tag={tag}"

        elif platform == "flipkart":
            tag = affiliate_tags.get("flipkart", "")
            if tag and "affid=" not in url and "aff_id=" not in url:
                separator = "&" if "?" in url else "?"
                tagged_url = f"{url}{separator}affid={tag}"

        elif platform == "meesho":
            tag = affiliate_tags.get("meesho", "")
            if tag and "ref=" not in url:
                separator = "&" if "?" in url else "?"
                tagged_url = f"{url}{separator}ref={tag}"

        tagged_link = link.copy()
        tagged_link["url"] = tagged_url
        tagged_links.append(tagged_link)

    return tagged_links


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def format_response(product_name: str, links: List[Dict]) -> str:
    """Format the DM response with affiliate links"""
    if not links:
        return f"❌ No affiliate links found for \"{product_name}\".\n\nTry a more specific product name?"

    link_lines = []
    for link in links:
        platform = link.get("platform", "Unknown")
        url = link.get("url", "#")
        commission = link.get("commission", "?")
        link_lines.append(f"🔗 {platform} (Commission: {commission})\n{url}")

    links_text = "\n\n".join(link_lines)

    return f"""🛍️ Found: {product_name}

{links_text}

👉 Click any link to support me!
💰 Your purchase helps me create better content"""


# ============================================================================
# DM HANDLING
# ============================================================================

def get_unread_dms() -> List[Any]:
    """Get unread direct messages"""
    try:
        threads = cl.direct_threads(amount=20)
        unread = []

        for thread in threads:
            if thread.unread_count > 0:
                for message in thread.messages:
                    if message.id not in processed_message_ids:
                        unread.append({
                            "thread_id": thread.id,
                            "message_id": message.id,
                            "user_id": message.user_id,
                            "text": message.text,
                            "timestamp": message.timestamp
                        })

        return unread
    except Exception as e:
        logger.error(f"Error fetching DMs: {e}")
        return []


def send_dm_reply(user_id: str, text: str) -> bool:
    """Send a DM reply to user"""
    try:
        cl.direct_send(text, user_ids=[user_id])
        logger.info(f"Sent reply to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send DM: {e}")
        return False


def mark_as_read(thread_id: str) -> bool:
    """Mark thread as read"""
    try:
        cl.direct_thread(thread_id).mark_as_read()
        return True
    except Exception as e:
        logger.error(f"Failed to mark as read: {e}")
        return False


def handle_dm(dm: Dict) -> bool:
    """Process a single DM"""
    message_id = dm["message_id"]
    user_id = dm["user_id"]
    text = dm.get("text", "")
    thread_id = dm["thread_id"]

    logger.info(f"Processing DM from {user_id}: {text[:100]}...")

    if message_id in processed_message_ids:
        return True

    try:
        product_name = extract_product_from_message(text)

        if not product_name:
            help_msg = f"""🤖 How to use {config.BOT_NAME}:

1️⃣ Send a product name:
   "iPhone 15 Pro Max"

2️⃣ Or send an Instagram Reel URL:
   "https://www.instagram.com/reel/abc123/"

3️⃣ I'll reply with my affiliate links:
   • Amazon (3-5% commission)
   • Flipkart (4-6% commission)
   • Meesho (5-10% commission)

💡 Tip: Click "Visit" to open in app, or "Copy" to share!

❓ Issues? Make sure the reel is public."""
            send_dm_reply(user_id, help_msg)
            processed_message_ids.add(message_id)
            mark_as_read(thread_id)
            return True

        logger.info(f"Extracted product: {product_name}")

        links = search_affiliate_links(product_name)

        if links is None:
            send_dm_reply(user_id, "❌ Couldn't fetch links right now. Please try again in a minute.")
            return False

        affiliate_tags = {
            "amazon": config.AMAZON_ASSOCIATE_TAG,
            "flipkart": config.FLIPKART_AFFILIATE_ID,
            "meesho": config.MEESHO_AFFILIATE_ID,
        }
        tagged_links = add_affiliate_tags(links, affiliate_tags)

        response = format_response(product_name, tagged_links)
        success = send_dm_reply(user_id, response)

        if success:
            processed_message_ids.add(message_id)
            mark_as_read(thread_id)

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "product_name": product_name,
                "platforms": [l.get("platform") for l in tagged_links],
                "link_count": len(tagged_links)
            }
            logger.info(f"Interaction: {json.dumps(log_entry)}")

        return success

    except Exception as e:
        logger.error(f"Error handling DM: {e}")
        send_dm_reply(user_id, "❌ Failed to send reply. Please try again.")
        return False


# ============================================================================
# MAIN BOT LOOP
# ============================================================================

def check_dms():
    """Main function to check and process DMs"""
    global processed_message_ids

    if not login():
        logger.error("Login failed, skipping cycle")
        return

    try:
        unread_dms = get_unread_dms()
        logger.info(f"Found {len(unread_dms)} unread DMs")

        processed = 0
        for dm in unread_dms[:config.MAX_DMS_PER_CYCLE]:
            if handle_dm(dm):
                processed += 1
            time.sleep(2)

        logger.info(f"Processed {processed}/{len(unread_dms)} DMs")

    except Exception as e:
        logger.error(f"Error in check_dms: {e}")


def run_bot():
    """Run the bot continuously"""
    logger.info(f"🤖 Starting {config.BOT_NAME}...")
    logger.info(f"Checking DMs every {config.CHECK_INTERVAL} seconds")

    if not setup_client():
        logger.error("Failed to setup client")
        return

    if not login():
        logger.error("Initial login failed")
        return

    schedule.every(config.CHECK_INTERVAL).seconds.do(check_dms)

    check_dms()

    logger.info("Bot running... Press Ctrl+C to stop")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        try:
            cl.dump_settings(config.SESSION_FILE)
            logger.info("Session saved")
        except:
            pass


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if config.INSTAGRAM_USERNAME.startswith("your_") or config.INSTAGRAM_PASSWORD.startswith("your_"):
        logger.error("❌ Please configure your Instagram credentials in .env file")
        logger.error("Copy .env.example to .env and fill in your values")
        exit(1)

    run_bot()