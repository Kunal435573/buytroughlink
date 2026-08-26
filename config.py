import os
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', 'your_bot_username')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', 'your_bot_password')

AMAZON_ASSOCIATE_TAG = os.getenv('AMAZON_ASSOCIATE_TAG', 'your-amazon-tag')
FLIPKART_AFFILIATE_ID = os.getenv('FLIPKART_AFFILIATE_ID', 'your-flipkart-id')
MEESHO_AFFILIATE_ID = os.getenv('MEESHO_AFFILIATE_ID', 'your-meesho-id')

API_BASE = os.getenv('API_BASE', 'http://localhost:8000')

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '30'))
MAX_DMS_PER_CYCLE = int(os.getenv('MAX_DMS_PER_CYCLE', '10'))
SESSION_FILE = os.getenv('SESSION_FILE', 'instagram_session.json')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
BOT_NAME = os.getenv('BOT_NAME', 'BuyMeLink Bot')