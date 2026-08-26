import os
from dotenv import load_dotenv
import requests
import schedule
import time
import logging
from instagrapi import Client
from config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BuyMeLinkBot:
    def __init__(self):
        self.client = Client()
        self.logged_in = False
    
    def login(self):
        """Login to Instagram"""
        try:
            logger.info("🔐 Logging into Instagram...")
            self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            self.logged_in = True
            logger.info("✅ Successfully logged in")
            return True
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def get_new_messages(self):
        """Fetch new DMs"""
        try:
            threads = self.client.direct_threads(limit=10)
            return threads
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def extract_product_name(self, message_text):
        """Extract product name from message"""
        if not message_text:
            return None
        
        if "instagram.com" in message_text:
            return None
        else:
            return message_text.strip()
    
    def search_affiliate_links(self, product_name):
        """Call FastAPI backend"""
        try:
            response = requests.get(
                f"{API_BASE}/search",
                params={"query": product_name},
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('links', [])
            else:
                logger.error(f"API error: {response.status_code}")
                return []
        except requests.exceptions.Timeout:
            logger.error("API timeout")
            return []
        except Exception as e:
            logger.error(f"Error calling API: {e}")
            return []
    
    def add_affiliate_ids(self, links):
        """Add your affiliate IDs to links"""
        formatted_links = []
        
        for link in links:
            platform = link.get('platform', '')
            url = link.get('url', '')
            commission = link.get('commission', '')
            
            if platform == 'Amazon' and AMAZON_ASSOCIATE_TAG:
                url = f"{url}&tag={AMAZON_ASSOCIATE_TAG}"
            elif platform == 'Flipkart' and FLIPKART_AFFILIATE_ID:
                url = f"{url}&aff_id={FLIPKART_AFFILIATE_ID}"
            elif platform == 'Meesho' and MEESHO_AFFILIATE_ID:
                url = f"{url}&ref={MEESHO_AFFILIATE_ID}"
            
            formatted_links.append({
                'platform': platform,
                'url': url,
                'commission': commission
            })
        
        return formatted_links
    
    def format_response(self, product_name, links):
        """Format DM response"""
        if not links:
            return f"Sorry, couldn't find links for '{product_name}'. Try another product!"
        
        message = f"🛍️ Found: {product_name}\n\n"
        
        for link in links:
            message += f"🔗 {link['platform']} ({link['commission']})\n"
            message += f"{link['url']}\n\n"
        
        message += "👉 Click any link to support me!\n"
        message += "💰 Your purchase helps me create better content"
        
        return message
    
    def send_dm(self, user_id, text):
        """Send DM to user"""
        try:
            self.client.direct_send(text, user_ids=[user_id])
            logger.info(f"✅ DM sent to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending DM: {e}")
            return False
    
    def process_messages(self):
        """Process new messages"""
        threads = self.get_new_messages()
        
        for thread in threads:
            for message in thread.messages:
                if message.is_own:
                    continue
                
                product_name = self.extract_product_name(message.text or "")
                
                if not product_name:
                    self.send_dm(thread.user.pk, "Send a product name (e.g., iPhone, AirPods)")
                    continue
                
                logger.info(f"🔍 Processing: {product_name}")
                
                links = self.search_affiliate_links(product_name)
                formatted_links = self.add_affiliate_ids(links)
                response = self.format_response(product_name, formatted_links)
                
                self.send_dm(thread.user.pk, response)
    
    def run(self):
        """Start the bot"""
        if not self.login():
            logger.error("Cannot start bot without login")
            return
        
        logger.info("🤖 Bot started!")
        logger.info("📨 Listening to DMs...")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            schedule.every(DM_CHECK_INTERVAL).seconds.do(self.process_messages)
            
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped")
        except Exception as e:
            logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    bot = BuyMeLinkBot()
    bot.run()