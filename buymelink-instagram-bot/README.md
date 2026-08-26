# BuyMeLink Instagram Bot

Affiliate link finder bot for Instagram DMs.

## Setup

1. Create Instagram bot account
2. Copy `.env.example` to `.env`
3. Add your credentials and affiliate IDs to `.env`
4. Install dependencies: `pip install -r requirements.txt`
5. Make sure FastAPI backend is running on `http://localhost:8000`
6. Run bot: `python bot.py`

## How It Works

- User sends product name to bot DM
- Bot calls FastAPI backend
- Backend searches affiliate links
- Bot adds your affiliate IDs
- Bot sends links back to user
- You earn commission!

## Requirements

- Python 3.8+
- Instagram account for bot
- Affiliate accounts (Amazon, Flipkart, Meesho)
- FastAPI backend running

## Troubleshooting

- Invalid credentials → Check .env
- Connection error → Backend not running
- No reply → Wait 30 seconds (bot checks DMs every 30s)