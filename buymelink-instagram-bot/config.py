import os
from dotenv import load_dotenv

load_dotenv()

# Instagram Credentials
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

# Your Affiliate IDs
AMAZON_ASSOCIATE_TAG = os.getenv('AMAZON_ASSOCIATE_TAG')
FLIPKART_AFFILIATE_ID = os.getenv('FLIPKART_AFFILIATE_ID')
MEESHO_AFFILIATE_ID = os.getenv('MEESHO_AFFILIATE_ID')

# API Configuration
API_BASE = "http://localhost:8000"
API_TIMEOUT = 10
DM_CHECK_INTERVAL = 30