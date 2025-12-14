import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_IDS = [int(uid) for uid in os.getenv('ADMIN_USER_IDS', '').split(',') if uid.strip()]

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'telegram_premium_bot')

# TronGrid Configuration
TRONGRID_API_KEY = os.getenv('TRONGRID_API_KEY', '')
USDT_TRC20_CONTRACT = os.getenv('USDT_TRC20_CONTRACT', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t')
PAYMENT_WALLET_ADDRESS = os.getenv('PAYMENT_WALLET_ADDRESS', '')

# Fragment Configuration
FRAGMENT_SESSION_FILE = os.getenv('FRAGMENT_SESSION_FILE', 'fragment_session.json')
FRAGMENT_API_TOKEN = os.getenv('FRAGMENT_API_TOKEN', '')
FRAGMENT_API_URL = os.getenv('FRAGMENT_API_URL', 'https://fragment.com/api')

# Premium Package Prices (in USDT)
PRICES = {
    3: float(os.getenv('PRICE_3_MONTHS', '5.00')),
    6: float(os.getenv('PRICE_6_MONTHS', '9.00')),
    12: float(os.getenv('PRICE_12_MONTHS', '15.00'))
}

# Payment Settings
PAYMENT_TIMEOUT = int(os.getenv('PAYMENT_TIMEOUT', '1800'))  # 30 minutes
PAYMENT_CHECK_INTERVAL = int(os.getenv('PAYMENT_CHECK_INTERVAL', '30'))  # 30 seconds

# TronGrid API URLs
TRONGRID_API_URL = 'https://api.trongrid.io'

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
