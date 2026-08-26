# BuyMeLink Instagram DM Bot

An automated Instagram DM bot that extracts product names from messages/reels, fetches affiliate links from your FastAPI backend, adds YOUR affiliate tags, and sends the links back to users.

## 🏗️ Architecture

```
User DMs bot (product name or reel URL)
         ↓
Bot extracts product name
         ↓
Bot calls FastAPI: GET /search?query=product
         ↓
FastAPI scrapes Amazon, Flipkart, Meesho
         ↓
Bot receives 3 affiliate links
         ↓
Bot adds YOUR affiliate IDs to each link
         ↓
Bot sends formatted DM back to user
         ↓
User clicks → Buys → Commission goes to YOU
```

## 📁 Project Structure

```
buymelink-backend/
├── main.py              # FastAPI backend (already working)
├── bot.py               # Instagram DM bot (NEW)
├── config.py            # Configuration constants
├── requirements.txt     # Python dependencies
├── .env.example         # Template for credentials
├── .env                 # Your actual credentials (create this)
├── instagram_session.json  # Auto-generated session file
└── bot.log              # Auto-generated log file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd buymelink-backend
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
# Instagram Bot Account (REQUIRED)
INSTAGRAM_USERNAME=your_bot_username
INSTAGRAM_PASSWORD=your_bot_password

# YOUR Affiliate IDs (Commission goes to YOU)
AMAZON_ASSOCIATE_TAG=your-amazon-tag
FLIPKART_AFFILIATE_ID=your-flipkart-id
MEESHO_AFFILIATE_ID=your-meesho-id

# Backend URL (usually no change needed)
API_BASE=http://localhost:8000
```

### 3. Start FastAPI Backend

```bash
# Terminal 1
python main.py
```

The backend runs on `http://localhost:8000` with endpoints:
- `GET /search?query=<product>` - Returns affiliate links
- `GET /products/trending` - Trending products
- `GET /analytics/stats` - Analytics

### 4. Start Instagram Bot

```bash
# Terminal 2
python bot.py
```

The bot will:
- Login to Instagram
- Check for new DMs every 30 seconds
- Process messages and reply with affiliate links

## 🔑 Getting Credentials

### Instagram Bot Account

1. Create a new Instagram account for your bot (or use existing)
2. Use the username/password in `.env`
3. **Important**: Enable 2FA and use an App Password if possible
4. The bot will create `instagram_session.json` for persistent login

### Amazon Associates (India)

1. Go to https://affiliate-program.amazon.in/
2. Sign up / Login
3. Get your **Associate Tag** (Tracking ID)
4. Format: `yourtag-21` (usually ends with -21)

### Flipkart Affiliate

1. Go to https://affiliate.flipkart.com/
2. Sign up / Login
3. Get your **Affiliate ID**
4. Format: usually alphanumeric string

### Meesho Affiliate

1. Go to https://meesho.com/affiliate
2. Sign up / Login
3. Get your **Referral ID**

## 💬 How It Works

### User sends product name:
```
User: iPhone 15 Pro Max
Bot:  🛍️ Found: iPhone 15 Pro Max

🔗 Amazon (Commission: 3-5%)
https://amazon.in/s?k=iPhone+15+Pro+Max&tag=YOUR_TAG

🔗 Flipkart (Commission: 4-6%)
https://www.flipkart.com/search?q=iPhone+15+Pro+Max&affid=YOUR_ID

🔗 Meesho (Commission: 5-10%)
https://www.meesho.com/search?q=iPhone+15+Pro+Max&ref=YOUR_ID

👉 Click any link to support me!
💰 Your purchase helps me create better content
```

### User sends Instagram Reel URL:
```
User: https://www.instagram.com/reel/ABC123xyz/
Bot:  🛍️ Found: iPhone 15 Pro (extracted from reel caption)

🔗 Amazon (Commission: 3-5%)
https://amazon.in/s?k=iPhone+15+Pro&tag=YOUR_TAG
...
```

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL` | 30 | Seconds between DM checks |
| `MAX_DMS_PER_CYCLE` | 10 | Max DMs to process per check |
| `SESSION_FILE` | instagram_session.json | Persistent login session |
| `LOG_FILE` | bot.log | Log file path |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## 📝 Logs

The bot creates two log files:
- `bot.log` - Application logs
- `instagram_session.json` - Instagram session (auto-managed)

Example log output:
```
2024-01-15 10:30:45 - __main__ - INFO - 🤖 Starting BuyMeLink Bot...
2024-01-15 10:30:45 - __main__ - INFO - Checking DMs every 30 seconds
2024-01-15 10:30:46 - __main__ - INFO - ✅ Login successful
2024-01-15 10:30:46 - __main__ - INFO - Bot running... Press Ctrl+C to stop
2024-01-15 10:31:15 - __main__ - INFO - Found 2 unread DMs
2024-01-15 10:31:15 - __main__ - INFO - Processing DM from 123456789: iPhone 15...
2024-01-15 10:31:16 - __main__ - INFO - Calling API: http://localhost:8000/search?query=iPhone 15
2024-01-15 10:31:17 - __main__ - INFO - API returned 3 links
2024-01-15 10:31:18 - __main__ - INFO - ✅ DM sent to 123456789
```

## 🐳 Docker Deployment (Optional)

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: .
    command: python main.py
    ports:
      - "8000:8000"
    env_file: .env

  bot:
    build: .
    command: python bot.py
    depends_on:
      - backend
    env_file: .env
    volumes:
      - ./instagram_session.json:/app/instagram_session.json
      - ./bot.log:/app/bot.log
```

Run with:
```bash
docker-compose up -d
```

## 🛠️ Troubleshooting

### Bot fails to login
- Check username/password in `.env`
- Delete `instagram_session.json` and restart
- Instagram may require 2FA verification on new device

### "Couldn't fetch links" error
- Ensure FastAPI backend is running on port 8000
- Check `API_BASE` in `.env` matches backend URL
- Test backend manually: `curl "http://localhost:8000/search?query=iPhone"`

### Bot not receiving DMs
- Make sure bot account can receive DMs (not restricted)
- Check Instagram app permissions
- Verify the bot isn't blocked by users

### Links not working
- Verify affiliate IDs are correct in `.env`
- Test affiliate links manually in browser
- Some programs require approval before links work

### Rate limiting
- Increase `CHECK_INTERVAL` if getting rate limited
- Reduce `MAX_DMS_PER_CYCLE`
- Add delays between API calls

## 🔒 Security Notes

- Never commit `.env` to git (add to `.gitignore`)
- Use strong passwords for bot account
- Enable 2FA on Instagram account
- Rotate credentials periodically
- Monitor `bot.log` for suspicious activity

## 📊 Monitoring

Check bot health:
```bash
# View recent logs
tail -f bot.log

# Check if bot is running
ps aux | grep bot.py

# Test API manually
curl "http://localhost:8000/search?query=test"
```

## 🤝 Business Model

| Party | Gets |
|-------|------|
| **Creator** | Views, engagement, content value |
| **User** | Product discovery, easy purchase |
| **You (Bot Owner)** | **Affiliate commission from all sales** |

The creator drives traffic → You monetize it → Win-win!

## 📄 License

MIT License - Feel free to use and modify.

## 🆘 Support

If you encounter issues:
1. Check `bot.log` for error details
2. Verify all credentials in `.env`
3. Ensure FastAPI backend is running
4. Check Instagram account status
5. Review rate limits