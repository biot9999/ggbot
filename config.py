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

# ============ Telegram API 配置 ============
# 用于 Telethon 登录 Telegram 并获取 Fragment 认证
# 默认使用公共 API（无需用户申请）
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', '2040'))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', 'b18441a1ff607e10a989891a5462e627')

# 用户手机号（需要配置，国际格式，如 +8613800138000）
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE', '')

# 2FA 密码（如果账号启用了两步验证）
TELEGRAM_2FA_PASSWORD = os.getenv('TELEGRAM_2FA_PASSWORD', '')

# Telethon Session 文件名（单个会话，向后兼容）
TELEGRAM_SESSION = os.getenv('TELEGRAM_SESSION', 'fragment_session')

# Telethon 多会话支持（用于用户名解析）
# 会话文件目录（存放 *.session 文件）
TELETHON_SESSIONS_DIR = os.getenv('TELETHON_SESSIONS_DIR', 'sessions')

# 优先级会话列表（逗号分隔的会话名，不带 .session 扩展名）
# 如果为空，将自动扫描 TELETHON_SESSIONS_DIR 目录
# 例如：'+34654041691,+8613800138000'
TELETHON_SESSIONS = os.getenv('TELETHON_SESSIONS', '')

# ============ Fragment 配置 ============
FRAGMENT_BOT_USERNAME = os.getenv('FRAGMENT_BOT_USERNAME', 'FragmentBot')

# 旧的 session 文件（向后兼容，将被弃用）
FRAGMENT_SESSION_FILE = os.getenv('FRAGMENT_SESSION_FILE', 'fragment_session.json')

# 会员套餐配置
PREMIUM_PLANS = {
    3: {'price_ton': 7.69, 'discount': '-20%'},
    6: {'price_ton': 10.25, 'discount': '-47%'},
    12: {'price_ton': 18.59, 'discount': '-52%'}
}

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
