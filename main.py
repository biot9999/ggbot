#!/usr/bin/env python3
"""
Telegram Premium Bot - Single File Version
All modules merged into one file for easier deployment.
config.py remains separate for configuration management.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import logging
import asyncio
import qrcode
import io
import uuid
import random
import json
import re
import aiohttp
import time
import tempfile
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Configuration module is kept separate
import config

# Import Fragment modules
from fragment_premium import FragmentPremium

# Import Telethon resolver
from telethon_resolver import get_resolver

# ============================================================================
# CONSTANTS
# ============================================================================

# Order status
ORDER_STATUS = {
    'pending': '⏳ 待支付',
    'paid': '💰 已支付',
    'completed': '✅ 已完成',
    'failed': '❌ 失败',
    'expired': '⏰ 已过期',
    'cancelled': '🚫 已取消'
}

ORDER_STATUS_EMOJI = {
    'pending': '⏳',
    'paid': '💰',
    'completed': '✅',
    'failed': '❌',
    'expired': '⏰',
    'cancelled': '🚫'
}

# Product types
PRODUCT_TYPE_PREMIUM = 'premium'
PRODUCT_TYPE_STARS = 'stars'
PRODUCT_TYPE_RECHARGE = 'recharge'

# Gift types
GIFT_TYPE_SELF = 'self'
GIFT_TYPE_OTHER = 'other'

# User state keys
STATE_AWAITING_RECIPIENT = 'awaiting_recipient'
STATE_AWAITING_STARS_AMOUNT = 'awaiting_stars_amount'

# Premium package options
PREMIUM_PACKAGES = [3, 6, 12]

# Stars package options (quantity)
STARS_PACKAGES = [100, 250, 500, 1000, 2500]

# Error messages
ERROR_MSG_FRAGMENT_GIFTING_FAILED = "Fragment service error during Premium gifting"

logger = logging.getLogger(__name__)

# ============================================================================
# NAMESPACE CLASSES
# ============================================================================

class MessageNamespace:
    """Namespace for message functions"""
    pass

class KeyboardNamespace:
    """Namespace for keyboard functions"""
    pass

class UtilsNamespace:
    """Namespace for utility functions"""
    pass

# Create namespace instances
messages = MessageNamespace()
keyboards = KeyboardNamespace()
utils = UtilsNamespace()

def format_time_remaining(expires_at) -> str:
    """Format remaining time until expiration"""
    if isinstance(expires_at, (int, float)):
        expires_dt = datetime.fromtimestamp(expires_at)
    else:
        expires_dt = expires_at
    
    remaining = expires_dt - datetime.now()
    
    if remaining.total_seconds() <= 0:
        return "已过期"
    
    minutes = int(remaining.total_seconds() / 60)
    seconds = int(remaining.total_seconds() % 60)
    
    if minutes > 0:
        return f"{minutes}分{seconds}秒"
    else:
        return f"{seconds}秒"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_username(username: str) -> bool:
    """Validate Telegram username format"""
    if not username:
        return False
    
    # Remove @ if present
    username = username.lstrip('@')
    
    # Username should be 5-32 characters, alphanumeric and underscores
    if len(username) < 5 or len(username) > 32:
        return False
    
    # Check if contains only valid characters
    return username.replace('_', '').isalnum()

def validate_user_id(user_id_str: str) -> Optional[int]:
    """Validate and convert user ID string to int"""
    try:
        user_id = int(user_id_str)
        if user_id > 0:
            return user_id
    except (ValueError, TypeError):
        pass
    return None

def get_product_name(product_type: str, months: int = None, stars: int = None) -> str:
    """Get formatted product name"""
    if product_type == 'premium' and months:
        return f"{months}个月 Telegram Premium"
    elif product_type == 'stars' and stars:
        return f"{stars} Telegram Stars"
    return "未知商品"

def calculate_success_rate(completed: int, total: int) -> float:
    """Calculate success rate percentage"""
    if total == 0:
        return 0.0
    return (completed / total) * 100

def get_date_range(period: str) -> tuple:
    """Get date range for statistics
    
    Args:
        period: 'today', 'week', 'month', or 'all'
    
    Returns:
        tuple of (start_date, end_date)
    """
    now = datetime.now()
    
    if period == 'today':
        start = datetime(now.year, now.month, now.day)
        end = now
    elif period == 'week':
        start = now - timedelta(days=7)
        end = now
    elif period == 'month':
        start = now - timedelta(days=30)
        end = now
    else:  # 'all'
        # Use a reasonable past date that won't cause timezone issues
        start = datetime(2020, 1, 1)
        end = now
    
    return start, end

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_currency(amount: float) -> str:
    """Format currency amount"""
    return f"${amount:.2f}"

def generate_unique_price(base_price: float) -> float:
    """
    Generate unique payment amount by adding small random decimal
    Adds 0.0001-0.0099 to avoid payment confusion when multiple users pay same amount
    
    Args:
        base_price: Base price in USDT
    
    Returns:
        Unique price with 4 decimal places
    """
    random_cents = random.randint(1, 99) / 10000  # 0.0001 to 0.0099
    unique_price = base_price + random_cents
    return round(unique_price, 4)

def parse_recipient_input(input_text: str) -> Dict[str, Optional[str]]:
    """Parse recipient input (username or user ID)
    
    Returns:
        dict with 'type' ('username' or 'user_id') and 'value'
    """
    input_text = input_text.strip()
    
    # Check if it's a user ID (numeric)
    if input_text.isdigit():
        user_id = validate_user_id(input_text)
        if user_id:
            return {'type': 'user_id', 'value': user_id}
    
    # Check if it's a username
    if input_text.startswith('@'):
        username = input_text[1:]
    else:
        username = input_text
    
    if validate_username(username):
        return {'type': 'username', 'value': username}
    
    return {'type': None, 'value': None}

def get_order_summary(order: Dict) -> str:
    """Get a brief order summary"""
    
    status_emoji = ORDER_STATUS_EMOJI.get(order.get('status', 'pending'), '❓')
    product_name = order.get('product_name', f"{order.get('months', 0)}个月 Premium")
    
    return f"{status_emoji} {product_name} - ${order['price']:.2f}"

async def send_long_message(context, chat_id: int, text: str, **kwargs):
    """Send message, splitting if too long (Telegram has 4096 char limit)"""
    max_length = 4000  # Leave some margin
    
    if len(text) <= max_length:
        await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    else:
        # Split by paragraphs
        parts = text.split('\n\n')
        current_part = ""
        
        for part in parts:
            if len(current_part) + len(part) + 2 <= max_length:
                if current_part:
                    current_part += "\n\n"
                current_part += part
            else:
                if current_part:
                    await context.bot.send_message(chat_id=chat_id, text=current_part, **kwargs)
                current_part = part
        
        if current_part:
            await context.bot.send_message(chat_id=chat_id, text=current_part, **kwargs)

def log_order_action(order_id: str, action: str, details: str = ""):
    """Log order-related actions"""
    logger.info(f"Order {order_id[:8]}... - {action} - {details}")

def log_payment_action(tx_hash: str, action: str, details: str = ""):
    """Log payment-related actions"""
    logger.info(f"Payment {tx_hash[:8]}... - {action} - {details}")

def log_user_action(user_id: int, action: str, details: str = ""):
    """Log user-related actions"""
    logger.info(f"User {user_id} - {action} - {details}")

async def safe_edit_message(message, text: str = None, caption: str = None, 
                           reply_markup=None, parse_mode: str = None):
    """
    Safely edit a message, handling both photo+caption and text messages
    
    This helper handles cases where:
    - Original message is a photo with caption -> use edit_message_caption
    - Original message is text -> use edit_message_text
    - Edit fails -> fall back to sending a new message
    
    Args:
        message: The message object to edit
        text: Text content (for text messages)
        caption: Caption content (for photo messages)
        reply_markup: Optional keyboard markup
        parse_mode: Optional parse mode (Markdown, HTML)
    
    Returns:
        bool: True if edit/send succeeded, False otherwise
    """
    try:
        # Determine if this is a photo message or text message
        is_photo = message.photo is not None and len(message.photo) > 0
        
        if is_photo:
            # For photo messages, use edit_message_caption
            content = caption if caption is not None else text
            if content is not None:
                await message.edit_caption(
                    caption=content,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                # Just update keyboard
                await message.edit_reply_markup(reply_markup=reply_markup)
            logger.debug("Successfully edited photo caption")
            return True
        else:
            # For text messages, use edit_message_text
            content = text if text is not None else caption
            if content is not None:
                await message.edit_text(
                    text=content,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                # Just update keyboard
                await message.edit_reply_markup(reply_markup=reply_markup)
            logger.debug("Successfully edited text message")
            return True
            
    except Exception as e:
        # If edit fails (e.g., message too old, identical content), try sending new message
        logger.warning(f"Failed to edit message: {e}. Attempting to send new message.")
        try:
            content = text or caption
            if content:
                await message.reply_text(
                    text=content,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                logger.debug("Sent new message as fallback")
                return True
        except Exception as e2:
            logger.error(f"Failed to send fallback message: {e2}")
            return False
    
    return False

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    """Main menu with 2-column grid layout"""
    keyboard = [
        [
            InlineKeyboardButton("💎 购买会员", callback_data="menu_buy_premium"),
            InlineKeyboardButton("⭐ 购买星星", callback_data="menu_buy_stars")
        ],
        [
            InlineKeyboardButton("👤 用户中心", callback_data="menu_user_center"),
            InlineKeyboardButton("📋 我的订单", callback_data="menu_my_orders")
        ],
        [
            InlineKeyboardButton("💰 充值余额", callback_data="menu_recharge")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_premium_packages_keyboard(prices):
    """Premium package selection keyboard"""
    keyboard = [
        [InlineKeyboardButton(f"💎 3个月 - ${prices[3]:.2f} USDT", callback_data="buy_premium_3")],
        [InlineKeyboardButton(f"💎 6个月 - ${prices[6]:.2f} USDT", callback_data="buy_premium_6")],
        [InlineKeyboardButton(f"💎 12个月 - ${prices[12]:.2f} USDT", callback_data="buy_premium_12")],
        [InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_purchase_type_keyboard(months):
    """Choose purchase for self or gift to others"""
    keyboard = [
        [InlineKeyboardButton("💎 为此账号购买", callback_data=f"purchase_self_{months}")],
        [InlineKeyboardButton("🎁 为他人购买", callback_data=f"purchase_gift_{months}")],
        [InlineKeyboardButton("↩️ 返回", callback_data="back_to_buy")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stars_packages_keyboard(prices):
    """Stars package selection keyboard"""
    keyboard = []
    for stars in [100, 250, 500, 1000, 2500]:
        price = prices.get(stars, stars * 0.01)  # Default price if not set
        keyboard.append([InlineKeyboardButton(
            f"⭐ {stars} 星星 - ${price:.2f} USDT", 
            callback_data=f"buy_stars_{stars}"
        )])
    keyboard.append([InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_payment_keyboard(order_id):
    """Payment action buttons"""
    keyboard = [
        [InlineKeyboardButton("✅ 我已支付", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ 取消订单", callback_data=f"cancel_{order_id}")],
        [InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_order_details_keyboard(order_id):
    """Order details action buttons"""
    keyboard = [
        [InlineKeyboardButton("🔍 查看详情", callback_data=f"order_detail_{order_id}")],
        [InlineKeyboardButton("↩️ 返回", callback_data="menu_my_orders")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_center_keyboard():
    """User center navigation buttons"""
    keyboard = [
        [InlineKeyboardButton("📋 查看订单", callback_data="menu_my_orders")],
        [InlineKeyboardButton("💎 购买会员", callback_data="menu_buy_premium")],
        [InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_orders_pagination_keyboard(page, total_pages, user_id):
    """Orders list with pagination"""
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ 上一页", callback_data=f"orders_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("下一页 ▶️", callback_data=f"orders_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard():
    """Admin panel buttons"""
    keyboard = [
        [InlineKeyboardButton("💰 查看余额", callback_data="admin_balance")],
        [InlineKeyboardButton("💵 设置价格", callback_data="admin_prices")],
        [InlineKeyboardButton("📊 统计面板", callback_data="admin_stats")],
        [InlineKeyboardButton("🔐 登录 Fragment", callback_data="admin_login")],
        [InlineKeyboardButton("📋 订单管理", callback_data="admin_orders")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_stats_keyboard():
    """Admin statistics panel buttons"""
    keyboard = [
        [InlineKeyboardButton("📊 订单统计", callback_data="admin_stats_orders")],
        [InlineKeyboardButton("💰 收入统计", callback_data="admin_stats_income")],
        [InlineKeyboardButton("👥 用户统计", callback_data="admin_stats_users")],
        [InlineKeyboardButton("↩️ 返回", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_main_keyboard():
    """Simple back to main menu button"""
    keyboard = [[InlineKeyboardButton("↩️ 返回主菜单", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Cancel current operation button"""
    keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_operation")]]
    return InlineKeyboardMarkup(keyboard)

def get_gift_confirmation_keyboard(order_data):
    """Gift confirmation keyboard with confirm and cancel buttons"""
    keyboard = [
        [InlineKeyboardButton("✅ 确认赠送", callback_data=f"confirm_gift_{order_data}")],
        [InlineKeyboardButton("❌ 取消", callback_data="cancel_gift")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_recharge_confirmation_keyboard(amount):
    """Recharge confirmation keyboard"""
    keyboard = [
        [InlineKeyboardButton("✅ 确认充值", callback_data=f"confirm_recharge_{amount}")],
        [InlineKeyboardButton("❌ 取消", callback_data="cancel_recharge")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_message(first_name, is_admin=False):
    """Welcome message for /start command"""
    message = f"""
🎉 欢迎使用 Telegram Premium 购买机器人！

👋 你好，{first_name}！

✨ 我们提供：
💎 Telegram Premium 会员
⭐ Telegram Stars 星星
🎁 支持赠送给好友

💰 支付方式：
• USDT (TRC20) 安全支付
• 自动验证，即时到账

⚡ 快速开通：
• 支付后自动处理
• 无需等待人工确认

请选择您需要的服务：
"""
    
    if is_admin:
        message += """
━━━━━━━━━━━━━━
👑 管理员功能：
/admin - 管理员面板
/setprice - 设置价格
/balance - 查看余额（提示信息）
/login - 查看 Fragment 配置状态
"""
    
    return message

def get_buy_premium_message(prices):
    """Premium purchase page message"""
    message = """
💎 **Telegram Premium 会员**

✨ Premium 特权包括：
• 📁 上传 4GB 大文件
• ⚡ 更快的下载速度
• 🎨 独家贴纸和表情
• 👤 专属头像边框
• 🔊 语音转文字功能
• 📊 高级统计数据
• 🎯 更多聊天置顶
• 🌟 专属标识

━━━━━━━━━━━━━━
📦 **套餐价格对比**

"""
    
    for months in [3, 6, 12]:
        price = prices[months]
        monthly_price = price / months
        savings = ""
        if months == 6:
            savings = f" 💰节省 {(prices[3]*2 - price):.2f} USDT"
        elif months == 12:
            savings = f" 💰节省 {(prices[3]*4 - price):.2f} USDT"
        
        message += f"💎 **{months}个月** - ${price:.2f} USDT (${monthly_price:.2f}/月){savings}\n"
    
    message += """
━━━━━━━━━━━━━━
⚡ **购买流程**
1️⃣ 选择套餐
2️⃣ 选择购买方式（自用/赠送）
3️⃣ USDT 支付
4️⃣ 自动开通

🔒 **安全保障**
✓ 区块链自动验证
✓ 真实 USDT 检测
✓ 支付即时确认

请选择套餐：
"""
    return message

def get_buy_stars_message(prices):
    """Stars purchase page message"""
    message = """
⭐ **Telegram Stars 星星**

✨ 星星用途：
• 🎁 赠送给内容创作者
• 🤖 使用 Bot 高级功能
• 🎮 购买游戏内物品
• 💬 解锁专属内容

━━━━━━━━━━━━━━
📦 **星星套餐**

"""
    
    for stars in [100, 250, 500, 1000, 2500]:
        price = prices.get(stars, stars * 0.01)
        message += f"⭐ **{stars} 星星** - ${price:.2f} USDT\n"
    
    message += """
━━━━━━━━━━━━━━
⚡ **购买流程**
1️⃣ 选择数量
2️⃣ USDT 支付
3️⃣ 自动充值

请选择套餐：
"""
    return message

def get_purchase_type_message(months, price):
    """Choose purchase for self or gift"""
    message = f"""
💎 **{months}个月 Telegram Premium**
💰 价格：${price:.2f} USDT

请选择购买方式：

💎 **为此账号购买**
   直接为您的账号开通 Premium

🎁 **为他人购买**
   购买后赠送给朋友
   需要提供对方的 @username 或 User ID
"""
    return message

def get_payment_message(order_id, product_name, price, wallet_address, expires_in_minutes=30):
    """Payment information message"""
    message = f"""
📦 **订单详情**
━━━━━━━━━━━━━━
🆔 订单号：
`{order_id}`

📦 商品：{product_name}
💰 订单金额：${price:.4f} USDT
💵 实付金额：${price:.4f} USDT

━━━━━━━━━━━━━━

💳 **付款信息**

🔹 网络：TRC20 (Tron)
🔹 代币：USDT
🔹 地址：
`{wallet_address}`

━━━━━━━━━━━━━━
⚠️ **重要提示**

1️⃣ 请确保使用 **TRC20 网络** 转账
2️⃣ 请转账准确金额：**${price:.4f} USDT**（包含所有小数位）
3️⃣ 转账后点击 "✅ 我已支付" 按钮
4️⃣ 系统将自动验证并开通
5️⃣ 订单有效期：**{expires_in_minutes} 分钟**

━━━━━━━━━━━━━━
🚫 **防诈骗提示**

✓ 请仔细核对收款地址
✓ 请使用真实 USDT（假币无法到账）
✓ 系统自动验证区块链交易
✓ 有任何问题请联系客服

⏱️ 请在 {expires_in_minutes} 分钟内完成支付
"""
    return message

def get_order_details_message(order):
    """Detailed order information"""
    status = order.get('status', 'pending')
    status_text = ORDER_STATUS.get(status, status)
    status_emoji = ORDER_STATUS_EMOJI.get(status, '❓')
    
    created_at = order.get('created_at', datetime.now())
    if isinstance(created_at, datetime):
        created_time = created_at.strftime('%Y-%m-%d %H:%M:%S')
    else:
        created_time = str(created_at)
    
    message = f"""
📋 **订单详情**
━━━━━━━━━━━━━━

{status_emoji} **订单状态**：{status_text}

🆔 **订单号**：
`{order['order_id']}`

📦 **商品信息**
• 商品：{order.get('product_name', f"{order['months']}个月 Telegram Premium")}
• 数量：1

💰 **金额信息**
• 订单金额：${order['price']:.2f} USDT
• 实付金额：${order['price']:.2f} USDT

👤 **购买信息**
• 购买用户：{order.get('username', 'N/A')}
• 下单时间：{created_time}

"""
    
    if order.get('tx_hash'):
        message += f"""
💳 **交易信息**
• 交易哈希：`{order['tx_hash']}`
"""
    
    if order.get('recipient_username'):
        message += f"""
🎁 **赠送信息**
• 赠送给：@{order['recipient_username']}
"""
    elif order.get('recipient_id'):
        message += f"""
🎁 **赠送信息**
• 赠送给：User ID {order['recipient_id']}
"""
    
    if status == 'completed' and order.get('completed_at'):
        completed_time = order['completed_at'].strftime('%Y-%m-%d %H:%M:%S')
        message += f"""
✅ **完成时间**：{completed_time}
"""
    
    return message

def get_user_center_message(user_id, username, stats):
    """User center with statistics"""
    balance = stats.get('balance', 0.0)
    
    message = f"""
👤 **用户中心**
━━━━━━━━━━━━━━

📱 **账号信息**
• 用户ID：`{user_id}`
• 用户名：@{username or 'N/A'}

💰 **余额信息**
• 可用余额：**${balance:.2f} USDT**

━━━━━━━━━━━━━━
📊 **购买统计**

📦 总订单数：**{stats['total_orders']}**
✅ 成功订单：**{stats['completed_orders']}**
⏳ 进行中：**{stats['pending_orders']}**
❌ 失败/取消：**{stats['failed_orders']}**

💰 总消费：**${stats['total_spent']:.2f} USDT**

━━━━━━━━━━━━━━
⭐ 感谢您的支持！
"""
    return message

def get_orders_list_message(orders, page=1, total_pages=1):
    """List of user orders with pagination"""
    if not orders:
        return "📭 您还没有任何订单\n\n点击下方按钮开始购买！"
    
    message = f"📋 **我的订单** (第 {page}/{total_pages} 页)\n"
    message += "━━━━━━━━━━━━━━\n\n"
    
    for order in orders:
        status = order.get('status', 'pending')
        status_emoji = ORDER_STATUS_EMOJI.get(status, '❓')
        status_text = ORDER_STATUS.get(status, status)
        
        product_name = order.get('product_name', f"{order.get('months', 0)}个月 Premium")
        created_at = order.get('created_at', datetime.now())
        if isinstance(created_at, datetime):
            time_str = created_at.strftime('%m-%d %H:%M')
        else:
            time_str = str(created_at)
        
        message += f"{status_emoji} **{product_name}** - {status_text}\n"
        message += f"   💰 ${order['price']:.2f} | 🕐 {time_str}\n"
        message += f"   🆔 `{order['order_id'][:8]}...`\n\n"
    
    return message

def get_admin_stats_message(stats):
    """Admin statistics panel message"""
    message = """
📊 **管理员统计面板**
━━━━━━━━━━━━━━


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================


"""
    
    # Order statistics
    message += """
📦 **订单统计**
"""
    message += f"• 总订单数：**{stats['orders']['total']}**\n"
    message += f"• 待支付：{stats['orders']['pending']}\n"
    message += f"• 已完成：{stats['orders']['completed']}\n"
    message += f"• 失败：{stats['orders']['failed']}\n"
    message += f"• 成功率：**{stats['orders']['success_rate']:.1f}%**\n\n"
    
    # Income statistics
    message += """
━━━━━━━━━━━━━━
💰 **收入统计**
"""
    message += f"• 今日收入：**${stats['income']['today']:.2f}**\n"
    message += f"• 本周收入：**${stats['income']['week']:.2f}**\n"
    message += f"• 本月收入：**${stats['income']['month']:.2f}**\n"
    message += f"• 总收入：**${stats['income']['total']:.2f}**\n\n"
    
    # User statistics
    message += """
━━━━━━━━━━━━━━
👥 **用户统计**
"""
    message += f"• 总用户数：**{stats['users']['total']}**\n"
    message += f"• 今日新增：{stats['users']['today']}\n"
    message += f"• 活跃用户：{stats['users']['active']}\n"
    
    return message

def get_help_message():
    """Help message"""
    return """
📖 **使用帮助**

━━━━━━━━━━━━━━
💎 **购买流程**

1️⃣ 点击 "💎 购买会员" 选择套餐
2️⃣ 选择是自用还是赠送他人
3️⃣ 扫描二维码或复制地址
4️⃣ 使用 USDT (TRC20) 支付
5️⃣ 点击 "✅ 我已支付" 按钮
6️⃣ 等待自动验证和开通（通常1-5分钟）

━━━━━━━━━━━━━━
⚠️ **注意事项**

• 请确保使用 **TRC20** 网络转账
• 请转账 **准确金额**
• 请使用 **真实 USDT**（假币无法到账）
• 订单有效期：**30 分钟**

━━━━━━━━━━━━━━
❓ **常见问题**

**Q: 支付后多久到账？**
A: 通常 1-5 分钟，最长不超过 30 分钟

**Q: 可以赠送给好友吗？**
A: 可以！选择 "🎁 为他人购买" 即可

**Q: 支持退款吗？**
A: 数字商品一经开通不支持退款

**Q: 支付遇到问题怎么办？**
A: 请联系管理员处理

━━━━━━━━━━━━━━
📞 需要帮助？请联系管理员
"""

def get_cancel_message():
    """Operation cancelled message"""
    return "❌ 操作已取消\n\n使用 /start 返回主菜单"

def get_recharge_message():
    """Recharge balance message"""
    return """
💰 **充值余额**

✨ 充值后可用余额购买会员或星星
💳 支持 USDT (TRC20) 支付

━━━━━━━━━━━━━━
📝 **充值流程**

1️⃣ 输入充值金额（USDT）
2️⃣ 扫描二维码支付
3️⃣ 自动到账，即可使用

━━━━━━━━━━━━━━
💡 **使用说明**

• 最低充值：5 USDT
• 最高充值：1000 USDT
• 余额可用于购买所有商品
• 支持部分余额+USDT组合支付

━━━━━━━━━━━━━━
请输入充值金额（例如：10）
或点击下方取消按钮
"""

def get_recharge_confirmation_message(amount):
    """Recharge confirmation message"""
    return f"""
💰 **确认充值信息**
━━━━━━━━━━━━━━

💵 充值金额：${amount:.2f} USDT
💳 到账金额：${amount:.2f} USDT

━━━━━━━━━━━━━━
⚠️ 请确认充值金额无误
点击「确认充值」继续支付
"""

def get_gift_confirmation_message(recipient_info, months, price):
    """Gift confirmation message with recipient details"""
    message = "🎁 **确认赠送信息**\n"
    message += "━━━━━━━━━━━━━━\n\n"
    
    # Recipient information
    message += "**收礼人信息：**\n"
    
    if recipient_info.get('photo_file_id'):
        message += f"📷 头像：已获取\n"
    
    if recipient_info.get('first_name') or recipient_info.get('last_name'):
        full_name = ' '.join(filter(None, [recipient_info.get('first_name'), recipient_info.get('last_name')]))
        message += f"👤 姓名：{full_name}\n"
    
    if recipient_info.get('username'):
        message += f"👤 用户名：@{recipient_info['username']}\n"
    elif recipient_info.get('user_id'):
        message += f"👤 User ID：`{recipient_info['user_id']}`\n"
    
    message += "\n━━━━━━━━━━━━━━\n"
    message += "**赠送套餐：**\n"
    message += f"💎 {months} 个月 Telegram Premium\n"
    message += f"💰 价格：${price:.2f} USDT\n\n"
    
    message += "━━━━━━━━━━━━━━\n"
    message += "⚠️ **请仔细核对收礼人信息**\n"
    message += "确认无误后点击「确认赠送」继续支付\n"
    
    return message

# ============================================================================
# ASSIGN FUNCTIONS TO NAMESPACES
# ============================================================================

# Assign message functions to messages namespace
messages.get_welcome_message = get_welcome_message
messages.get_buy_premium_message = get_buy_premium_message
messages.get_buy_stars_message = get_buy_stars_message
messages.get_purchase_type_message = get_purchase_type_message
messages.get_payment_message = get_payment_message
messages.get_order_details_message = get_order_details_message
messages.get_user_center_message = get_user_center_message
messages.get_orders_list_message = get_orders_list_message
messages.get_admin_stats_message = get_admin_stats_message
messages.get_help_message = get_help_message
messages.get_cancel_message = get_cancel_message
messages.get_recharge_message = get_recharge_message
messages.get_recharge_confirmation_message = get_recharge_confirmation_message
messages.get_gift_confirmation_message = get_gift_confirmation_message

# Assign keyboard functions to keyboards namespace
keyboards.get_main_menu_keyboard = get_main_menu_keyboard
keyboards.get_premium_packages_keyboard = get_premium_packages_keyboard
keyboards.get_purchase_type_keyboard = get_purchase_type_keyboard
keyboards.get_stars_packages_keyboard = get_stars_packages_keyboard
keyboards.get_payment_keyboard = get_payment_keyboard
keyboards.get_order_details_keyboard = get_order_details_keyboard
keyboards.get_user_center_keyboard = get_user_center_keyboard
keyboards.get_orders_pagination_keyboard = get_orders_pagination_keyboard
keyboards.get_admin_panel_keyboard = get_admin_panel_keyboard
keyboards.get_admin_stats_keyboard = get_admin_stats_keyboard
keyboards.get_back_to_main_keyboard = get_back_to_main_keyboard
keyboards.get_cancel_keyboard = get_cancel_keyboard
keyboards.get_gift_confirmation_keyboard = get_gift_confirmation_keyboard
keyboards.get_recharge_confirmation_keyboard = get_recharge_confirmation_keyboard

# Assign utility functions to utils namespace
utils.format_time_remaining = format_time_remaining
utils.validate_username = validate_username
utils.validate_user_id = validate_user_id
utils.get_product_name = get_product_name
utils.calculate_success_rate = calculate_success_rate
utils.get_date_range = get_date_range
utils.truncate_string = truncate_string
utils.format_currency = format_currency
utils.generate_unique_price = generate_unique_price
utils.parse_recipient_input = parse_recipient_input
utils.get_order_summary = get_order_summary
utils.log_order_action = log_order_action
utils.log_payment_action = log_payment_action
utils.log_user_action = log_user_action

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = MongoClient(config.MONGODB_URI)
        self.db = self.client[config.MONGODB_DB]
        self.users = self.db.users
        self.orders = self.db.orders
        self.transactions = self.db.transactions
        self.settings = self.db.settings
        self.gifts = self.db.gifts  # Gift records
        self.user_states = self.db.user_states  # User conversation states
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        self.users.create_index('user_id', unique=True)
        self.orders.create_index('order_id', unique=True)
        self.orders.create_index('user_id')
        self.orders.create_index('status')
        self.orders.create_index('created_at')
        self.transactions.create_index('tx_hash', unique=True)
        self.transactions.create_index('order_id')
        self.gifts.create_index('order_id')
        self.gifts.create_index('sender_id')
        self.gifts.create_index('recipient_id')
        self.user_states.create_index('user_id', unique=True)
    
    # User operations
    def create_user(self, user_id, username=None, first_name=None):
        """Create or update user"""
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        # Initialize balance if not exists
        self.users.update_one(
            {'user_id': user_id},
            {
                '$set': user_data,
                '$setOnInsert': {'balance': 0.0}
            },
            upsert=True
        )
        return user_data
    
    def get_user(self, user_id):
        """Get user by user_id"""
        return self.users.find_one({'user_id': user_id})
    
    def get_user_balance(self, user_id):
        """Get user's balance"""
        user = self.get_user(user_id)
        if user:
            return user.get('balance', 0.0)
        return 0.0
    
    def update_user_balance(self, user_id, amount, operation='add'):
        """Update user balance
        
        Args:
            user_id: User ID
            amount: Amount to add or subtract
            operation: 'add' or 'subtract'
        
        Returns:
            New balance or None if insufficient funds
        """
        if operation == 'add':
            result = self.users.update_one(
                {'user_id': user_id},
                {'$inc': {'balance': amount}, '$set': {'updated_at': datetime.now()}}
            )
            user = self.get_user(user_id)
            return user.get('balance', 0.0) if user else None
        elif operation == 'subtract':
            # Check if sufficient balance
            user = self.get_user(user_id)
            if not user or user.get('balance', 0.0) < amount:
                return None
            
            result = self.users.update_one(
                {'user_id': user_id},
                {'$inc': {'balance': -amount}, '$set': {'updated_at': datetime.now()}}
            )
            user = self.get_user(user_id)
            return user.get('balance', 0.0) if user else None
        
        return None
    
    # Order operations
    def create_order(self, order_id, user_id, months, price, product_type='premium', 
                     product_quantity=None, recipient_id=None, recipient_username=None,
                     balance_to_use=0.0, remaining_amount=None):
        """Create a new order
        
        Args:
            balance_to_use: Amount of user balance that will be used for this order
            remaining_amount: Amount remaining to be paid on-chain (None means use price)
        """
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'months': months,
            'price': price,
            'product_type': product_type,  # 'premium' or 'stars'
            'product_quantity': product_quantity,  # For stars
            'status': 'pending',  # pending, paid, completed, failed, expired, cancelled
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'payment_address': config.PAYMENT_WALLET_ADDRESS,
            'expires_at': datetime.now().timestamp() + config.PAYMENT_TIMEOUT,
            'recipient_id': recipient_id,  # For gifts
            'recipient_username': recipient_username,
            'balance_to_use': balance_to_use,  # Amount from user balance
            'remaining_amount': remaining_amount if remaining_amount is not None else price  # Amount to pay on-chain
        }
        self.orders.insert_one(order_data)
        return order_data
    
    def get_order(self, order_id):
        """Get order by order_id"""
        return self.orders.find_one({'order_id': order_id})
    
    def update_order_status(self, order_id, status, tx_hash=None, error=None):
        """Update order status
        
        Args:
            order_id: The order identifier
            status: New status value
            tx_hash: Optional transaction hash
            error: Optional error message. If provided, increments retry_count and stores error
            
        Returns:
            Optional[int]: The updated retry_count if error was provided, None otherwise.
                          Returns 0 if order not found (should not happen in normal operation).
        """
        update_data = {
            'status': status,
            'updated_at': datetime.now()
        }
        if tx_hash:
            update_data['tx_hash'] = tx_hash
        if status == 'completed':
            update_data['completed_at'] = datetime.now()
        
        # Handle error tracking with atomic increment
        if error:
            update_data['last_error'] = error
            # Use find_one_and_update for atomic retry count increment
            result = self.orders.find_one_and_update(
                {'order_id': order_id},
                {
                    '$set': update_data,
                    '$inc': {'retry_count': 1}
                },
                return_document=True  # Return the updated document
            )
            # Return updated retry_count, or 0 if order not found (shouldn't happen)
            if result:
                return result.get('retry_count', 0)
            else:
                logger.warning(f"Order {order_id} not found during status update with error")
                return 0
        else:
            self.orders.update_one(
                {'order_id': order_id},
                {'$set': update_data}
            )
            return None
    
    def get_pending_orders(self):
        """Get all pending orders"""
        return list(self.orders.find({'status': 'pending'}))
    
    def get_user_orders(self, user_id):
        """Get all orders for a user"""
        return list(self.orders.find({'user_id': user_id}).sort('created_at', -1))
    
    # Transaction operations
    def create_transaction(self, tx_hash, order_id, amount, from_address):
        """Record a transaction"""
        tx_data = {
            'tx_hash': tx_hash,
            'order_id': order_id,
            'amount': amount,
            'from_address': from_address,
            'created_at': datetime.now()
        }
        try:
            self.transactions.insert_one(tx_data)
            return tx_data
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
    
    def get_transaction(self, tx_hash):
        """Get transaction by hash"""
        return self.transactions.find_one({'tx_hash': tx_hash})
    
    def get_transaction_by_order(self, order_id):
        """Get transaction by order_id"""
        return self.transactions.find_one({'order_id': order_id})
    
    # Settings operations
    def get_setting(self, key):
        """Get a setting value"""
        setting = self.settings.find_one({'key': key})
        return setting['value'] if setting else None
    
    def set_setting(self, key, value):
        """Set a setting value"""
        self.settings.update_one(
            {'key': key},
            {'$set': {'key': key, 'value': value, 'updated_at': datetime.now()}},
            upsert=True
        )
    
    def get_prices(self):
        """Get current prices from database or config"""
        prices = {}
        for months in [3, 6, 12]:
            price = self.get_setting(f'price_{months}m')
            prices[months] = float(price) if price else config.PRICES[months]
        return prices
    
    def set_price(self, months, price):
        """Set price for a package"""
        self.set_setting(f'price_{months}m', price)
    
    # User state management
    def set_user_state(self, user_id, state, data=None):
        """Set user conversation state"""
        state_data = {
            'user_id': user_id,
            'state': state,
            'data': data or {},
            'updated_at': datetime.now()
        }
        self.user_states.update_one(
            {'user_id': user_id},
            {'$set': state_data},
            upsert=True
        )
    
    def get_user_state(self, user_id):
        """Get user conversation state"""
        return self.user_states.find_one({'user_id': user_id})
    
    def clear_user_state(self, user_id):
        """Clear user conversation state"""
        self.user_states.delete_one({'user_id': user_id})
    
    # Gift records
    def create_gift_record(self, order_id, sender_id, recipient_id, product_type, value):
        """Create a gift record"""
        gift_data = {
            'order_id': order_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'product_type': product_type,
            'value': value,  # months for premium, quantity for stars
            'created_at': datetime.now()
        }
        self.gifts.insert_one(gift_data)
        return gift_data
    
    def get_gifts_sent(self, user_id):
        """Get gifts sent by user"""
        return list(self.gifts.find({'sender_id': user_id}).sort('created_at', -1))
    
    def get_gifts_received(self, user_id):
        """Get gifts received by user"""
        return list(self.gifts.find({'recipient_id': user_id}).sort('created_at', -1))
    
    # Statistics methods
    def get_user_statistics(self, user_id):
        """Get statistics for a specific user"""
        orders = list(self.orders.find({'user_id': user_id}))
        
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o['status'] == 'completed'])
        pending_orders = len([o for o in orders if o['status'] in ['pending', 'paid']])
        failed_orders = len([o for o in orders if o['status'] in ['failed', 'cancelled', 'expired']])
        
        total_spent = sum(o['price'] for o in orders if o['status'] == 'completed')
        
        # Get balance
        balance = self.get_user_balance(user_id)
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'failed_orders': failed_orders,
            'total_spent': total_spent,
            'balance': balance
        }
    
    def get_order_statistics(self):
        """Get overall order statistics"""
        total = self.orders.count_documents({})
        pending = self.orders.count_documents({'status': 'pending'})
        paid = self.orders.count_documents({'status': 'paid'})
        completed = self.orders.count_documents({'status': 'completed'})
        failed = self.orders.count_documents({'status': {'$in': ['failed', 'cancelled', 'expired']}})
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'pending': pending,
            'paid': paid,
            'completed': completed,
            'failed': failed,
            'success_rate': success_rate
        }
    
    def get_income_statistics(self):
        """Get income statistics"""
        from datetime import timedelta
        
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # Today's income
        today_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': today_start}
        }))

# ============================================================================
# DATABASE MODULE
# ============================================================================


        today_income = sum(o['price'] for o in today_orders)
        
        # Week's income
        week_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': week_start}
        }))
        week_income = sum(o['price'] for o in week_orders)
        
        # Month's income
        month_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': month_start}
        }))
        month_income = sum(o['price'] for o in month_orders)
        
        # Total income
        all_completed = list(self.orders.find({'status': 'completed'}))
        total_income = sum(o['price'] for o in all_completed)
        
        return {
            'today': today_income,
            'week': week_income,
            'month': month_income,
            'total': total_income
        }
    
    def get_user_count_statistics(self):
        """Get user count statistics"""
        from datetime import timedelta
        
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
        total_users = self.users.count_documents({})
        
        # Today's new users
        today_users = self.users.count_documents({
            'created_at': {'$gte': today_start}
        })
        
        # Active users (users with at least one completed order)
        active_users = len(self.orders.distinct('user_id', {'status': 'completed'}))
        
        return {
            'total': total_users,
            'today': today_users,
            'active': active_users
        }
    
    def get_stars_prices(self):
        """Get stars prices from database or default"""
        prices = {}
        for stars in [100, 250, 500, 1000, 2500]:
            price = self.get_setting(f'stars_price_{stars}')
            prices[stars] = float(price) if price else stars * 0.01
        return prices
    
    def set_stars_price(self, stars, price):
        """Set price for stars package"""
        self.set_setting(f'stars_price_{stars}', price)

# Global database instance
db = Database()
import asyncio
import logging
import time
import json
from typing import Optional, Dict


# ============================================================================
# PAYMENT MODULE (TronGrid API)
# ============================================================================


logger = logging.getLogger(__name__)

# Retry and backoff configuration
MAX_RETRIES = 3
MAX_RETRY_BACKOFF = 30  # Maximum wait time between retries in seconds

class TronPayment:
    def __init__(self):
        self.api_url = config.TRONGRID_API_URL
        self.api_key = config.TRONGRID_API_KEY
        self.usdt_contract = config.USDT_TRC20_CONTRACT
        self.wallet_address = config.PAYMENT_WALLET_ADDRESS
        self.use_free_api = False  # Flag to track if we're using free API
        self.retry_count = 0
        self.max_retries = MAX_RETRIES
    
    def _get_headers(self, use_api_key=True):
        """Get headers for TronGrid API"""
        headers = {'Content-Type': 'application/json'}
        if use_api_key and self.api_key and not self.use_free_api:
            headers['TRON-PRO-API-KEY'] = self.api_key
        return headers
    
    def _should_fallback_to_free_api(self, status_code: int) -> bool:
        """Check if we should fallback to free API based on error code"""
        return status_code in [401, 403]
    
    async def get_account_transactions(self, address: str, limit: int = 20) -> Optional[list]:
        """Get TRC20 transactions for an address with automatic fallback to free API"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.api_url}/v1/accounts/{address}/transactions/trc20"
                params = {
                    'limit': limit,
                    'contract_address': self.usdt_contract
                }
                
                headers = self._get_headers(use_api_key=True)
                
                logger.debug(f"TronGrid API Request - URL: {url}")
                logger.debug(f"TronGrid API Request - Params: {params}")
                logger.debug(f"TronGrid API Request - Headers: {headers}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, headers=headers) as response:
                        response_text = await response.text()
                        logger.debug(f"TronGrid API Response - Status: {response.status}")
                        logger.debug(f"TronGrid API Response - Body: {response_text}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"Successfully fetched {len(data.get('data', []))} transactions")
                                return data.get('data', [])
                            except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                                logger.error(f"Error parsing response JSON: {e}")
                                return None
                                
                        elif self._should_fallback_to_free_api(response.status):
                            if not self.use_free_api:
                                logger.warning(
                                    f"TronGrid API {response.status} - Falling back to free public API. "
                                    f"Free API has rate limits: 5 requests/second, 10,000 requests/day"
                                )
                                self.use_free_api = True
                                # Retry with free API
                                continue
                            else:
                                logger.error(
                                    f"TronGrid Free API also returned {response.status}. "
                                    f"You may have exceeded rate limits."
                                )
                                # Wait before retry
                                await asyncio.sleep(min(2 ** attempt, MAX_RETRY_BACKOFF))
                                continue
                                
                        elif response.status == 429:
                            wait_time = min(2 ** attempt, MAX_RETRY_BACKOFF)
                            logger.warning(
                                f"TronGrid API 429 Too Many Requests - Rate limit exceeded. "
                                f"Waiting {wait_time}s before retry {attempt+1}/{self.max_retries}"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Failed to get transactions: HTTP {response.status} - {response_text}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error getting transactions (attempt {attempt+1}/{self.max_retries}): {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, MAX_RETRY_BACKOFF))
                else:
                    return None
        
        return None
    
    async def verify_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Verify a specific transaction with retry logic"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.api_url}/v1/transactions/{tx_hash}/info"
                headers = self._get_headers(use_api_key=True)
                
                logger.debug(f"TronGrid Verify TX Request - URL: {url}")
                logger.debug(f"TronGrid Verify TX Request - Headers: {headers}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        logger.debug(f"TronGrid Verify TX Response - Status: {response.status}")
                        logger.debug(f"TronGrid Verify TX Response - Body: {response_text}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"Transaction {tx_hash[:8]}... verified successfully")
                                return data
                            except Exception as e:
                                logger.error(f"Error parsing transaction response: {e}")
                                return None
                                
                        elif self._should_fallback_to_free_api(response.status):
                            if not self.use_free_api:
                                logger.warning(f"Falling back to free API for transaction verification")
                                self.use_free_api = True
                                continue
                            else:
                                logger.error(f"Free API also failed with status {response.status}")
                                await asyncio.sleep(min(2 ** attempt, MAX_RETRY_BACKOFF))
                                continue
                        else:
                            logger.error(f"Failed to verify transaction: HTTP {response.status} - {response_text}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error verifying transaction (attempt {attempt+1}/{self.max_retries}): {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, MAX_RETRY_BACKOFF))
                else:
                    return None
        
        return None
    
    async def check_payment(self, amount: float, timeout: int = 1800) -> Optional[Dict]:
        """
        Monitor for incoming payment of specified amount
        Returns transaction details if payment found within timeout
        """
        start_time = time.time()
        last_checked_timestamp = start_time * 1000  # Convert to milliseconds
        
        logger.info(f"Starting payment monitoring for amount: ${amount:.4f}")
        logger.debug(f"Monitor timeout: {timeout}s, check interval: {config.PAYMENT_CHECK_INTERVAL}s")
        
        while (time.time() - start_time) < timeout:
            try:
                logger.debug(f"Checking for payment... (elapsed: {int(time.time() - start_time)}s)")
                transactions = await self.get_account_transactions(self.wallet_address)
                
                if transactions:
                    logger.debug(f"Found {len(transactions)} recent transactions")
                    for tx in transactions:
                        tx_timestamp = tx.get('block_timestamp', 0)
                        
                        # Only check transactions after we started monitoring
                        if tx_timestamp < last_checked_timestamp:
                            continue
                        
                        # Check if transaction is to our wallet
                        if tx.get('to') != self.wallet_address:
                            logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... not to our wallet")
                            continue
                        
                        # Check if transaction is USDT TRC20
                        if tx.get('token_info', {}).get('address') != self.usdt_contract:
                            logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... not USDT")
                            continue
                        
                        # Check amount (convert from smallest unit)
                        tx_amount = float(tx.get('value', 0)) / (10 ** tx.get('token_info', {}).get('decimals', 6))
                        
                        logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... amount: ${tx_amount:.4f} (expected: ${amount:.4f})")
                        
                        # Use tight tolerance for unique amounts (0.00001 = 1/100 of smallest increment)
                        if abs(tx_amount - amount) < 0.00001:
                            logger.info(f"✅ Payment found! TX: {tx.get('transaction_id')}, Amount: ${tx_amount:.4f}")
                            return {
                                'tx_hash': tx.get('transaction_id'),
                                'amount': tx_amount,
                                'from': tx.get('from'),
                                'to': tx.get('to'),
                                'timestamp': tx_timestamp
                            }
                
                # Wait before next check
                await asyncio.sleep(config.PAYMENT_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error checking payment: {e}", exc_info=True)
                await asyncio.sleep(config.PAYMENT_CHECK_INTERVAL)
        
        logger.warning(f"Payment monitoring timeout after {timeout}s")
        return None
    
    async def verify_usdt_authenticity(self, tx_hash: str) -> bool:
        """
        Verify that the USDT transaction is real (not fake USDT)
        Checks if the token contract matches the official USDT TRC20 contract
        """
        try:
            logger.debug(f"Verifying USDT authenticity for TX: {tx_hash}")
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                logger.warning(f"Could not fetch transaction info for {tx_hash}")
                return False
            
            # Extract contract address from transaction
            trc20_transfers = tx_info.get('trc20_transfer', [])
            if not trc20_transfers:
                logger.warning(f"No TRC20 transfers found in transaction {tx_hash}")
                return False
            
            contract_address = trc20_transfers[0].get('token_address', '')
            
            logger.debug(f"Transaction contract: {contract_address}, Official USDT: {self.usdt_contract}")
            
            # Verify it's the official USDT contract
            if contract_address.upper() != self.usdt_contract.upper():
                logger.warning(f"⚠️ Fake USDT detected! TX: {tx_hash}, Contract: {contract_address}")
                return False
            
            logger.info(f"✅ Authentic USDT verified for TX: {tx_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying USDT authenticity: {e}", exc_info=True)
            return False
    
    async def get_transaction_details(self, tx_hash: str) -> Optional[Dict]:
        """Get detailed information about a transaction"""
        try:
            logger.debug(f"Fetching transaction details for: {tx_hash}")
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                logger.warning(f"No transaction info returned for {tx_hash}")
                return None
            
            # Extract relevant information
            trc20_transfers = tx_info.get('trc20_transfer', [])
            if not trc20_transfers:
                logger.warning(f"No TRC20 transfers in transaction {tx_hash}")
                return None
            
            transfer = trc20_transfers[0]
            
            details = {
                'tx_hash': tx_hash,
                'from': transfer.get('from_address', ''),
                'to': transfer.get('to_address', ''),
                'amount': float(transfer.get('amount_str', 0)) / 1000000,  # USDT has 6 decimals
                'token_address': transfer.get('token_address', ''),
                'timestamp': tx_info.get('block_timestamp', 0),
                'confirmed': tx_info.get('ret', [{}])[0].get('contractRet') == 'SUCCESS'
            }
            
            logger.debug(f"Transaction details: {details}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}", exc_info=True)
            return None

# Global payment instance
tron_payment = TronPayment()

# ============================================================================
# FRAGMENT MODULE (Fragment.com Integration)
# ============================================================================

class FragmentAutomationWrapper:
    """
    Wrapper class for FragmentPremium to maintain compatibility with existing code
    Uses Telethon + Fragment API instead of Playwright browser automation
    """
    
    def __init__(self):
        """Initialize Fragment automation wrapper"""
        self.premium = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def _ensure_initialized(self):
        """Ensure FragmentPremium is initialized"""
        async with self._lock:
            if not self._initialized or self.premium is None:
                try:
                    # Initialize FragmentPremium with config file
                    self.premium = FragmentPremium('fragment_auth.json')
                    
                    # Try to initialize (load auth from config)
                    # Run synchronous initialize in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    success = await loop.run_in_executor(None, self.premium.initialize)
                    
                    if success:
                        self._initialized = True
                        logger.info("✅ Fragment Premium initialized successfully")
                        return True
                    else:
                        logger.error("❌ Fragment Premium initialization failed")
                        logger.error("")
                        logger.error("📝 请配置 Fragment 认证：")
                        logger.error("1. 复制 fragment_auth.json.example 为 fragment_auth.json")
                        logger.error("2. 在浏览器登录 https://fragment.com")
                        logger.error("3. 从开发者工具获取 hash 和 cookies")
                        logger.error("4. 填入 fragment_auth.json")
                        logger.error("")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Error initializing Fragment Premium: {e}", exc_info=True)
                    return False
            
            return True
    
    @staticmethod
    async def check_playwright_dependencies():
        """
        Compatibility method - no longer checks Playwright dependencies
        Always returns success since we don't need browser or Telethon login anymore
        
        Returns:
            tuple: (True, None) - always succeeds
        """
        logger.info("ℹ️ Using manual auth Fragment integration (no browser/Telethon required)")
        return True, None
    
    async def login_with_telegram(self, max_retries=2):
        """
        Initialize Fragment with manual authentication
        
        Args:
            max_retries: Not used, kept for compatibility
            
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("🔐 开始 Fragment 初始化...")
            
            # Initialize (which loads auth from config)
            success = await self._ensure_initialized()
            
            if success:
                logger.info("✅ Fragment 初始化成功")
                return True
            else:
                logger.error("❌ Fragment 初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 初始化错误: {e}", exc_info=True)
            return False
    
    async def restore_session(self):
        """
        Restore saved session - compatibility method
        Just ensures initialization
        
        Returns:
            bool: True if session restored/initialized
        """
        return await self._ensure_initialized()
    
    async def get_balance(self):
        """
        Get Fragment account balance - compatibility method
        Note: Balance API may not be available, returns None
        
        Returns:
            float: Balance in TON, or None if failed
        """
        try:
            if not await self._ensure_initialized():
                logger.error("❌ Fragment not initialized")
                return None
            
            # Balance API doesn't exist in Fragment, return None
            logger.warning("⚠️ Fragment balance API is not available")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}", exc_info=True)
            return None
    
    async def gift_premium(self, user_id: int, months: int, max_retries: int = 3):
        """
        Gift Telegram Premium to a user
        
        Args:
            user_id: Telegram user ID of the recipient
            months: Number of months (3, 6, or 12)
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"🎁 Gifting {months} months Premium to user {user_id}")
        
        for attempt in range(max_retries):
            try:
                if not await self._ensure_initialized():
                    logger.error("❌ Fragment not initialized")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3)
                        continue
                    return False
                
                # Call the API to gift premium (run synchronous method in executor)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self.premium.gift_premium, 
                    user_id, 
                    months
                )
                
                if result.get('ok'):
                    logger.info(f"✅ Successfully gifted {months} months Premium to user {user_id}")
                    return True
                else:
                    error = result.get('error', 'Unknown error')
                    logger.error(f"❌ Failed to gift Premium: {error}")
                    
                    # Retry on certain errors
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                        await asyncio.sleep(3)
                        continue
                    
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error gifting premium (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)
                    continue
                return False
        
        return False
    
    async def close(self):
        """Close Fragment connection"""
        try:
            if self.premium:
                await self.premium.close()
                logger.info("Fragment connection closed")
        except Exception as e:
            logger.error(f"Error closing Fragment: {e}")

# Global fragment instance
fragment = FragmentAutomationWrapper()

# ============================================================================
# BOT HANDLERS AND MAIN LOGIC
# ============================================================================

# Configure logging
log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

# Active payment monitoring tasks
payment_tasks = {}

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.ADMIN_USER_IDS

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show main menu"""
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name)
    
    welcome_message = messages.get_welcome_message(user.first_name, is_admin(user.id))
    keyboard = keyboards.get_main_menu_keyboard()
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    utils.log_user_action(user.id, "Started bot", user.username)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command - cancel current operation"""
    user = update.effective_user
    db.clear_user_state(user.id)
    
    message = messages.get_cancel_message()
    keyboard = keyboards.get_main_menu_keyboard()
    
    await update.message.reply_text(message, reply_markup=keyboard)
    utils.log_user_action(user.id, "Cancelled operation")

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command - show Premium packages"""
    prices = db.get_prices()
    message = messages.get_buy_premium_message(prices)
    keyboard = keyboards.get_premium_packages_keyboard(prices)
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show user center"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    stats = db.get_user_statistics(user_id)
    message = messages.get_user_center_message(user_id, username, stats)
    keyboard = keyboards.get_user_center_keyboard()
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    message = messages.get_help_message()
    keyboard = keyboards.get_back_to_main_keyboard()
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

# ============================================================================
# ADMIN COMMAND HANDLERS
# ============================================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    keyboard = keyboards.get_admin_panel_keyboard()
    await update.message.reply_text("👑 管理员面板", reply_markup=keyboard)

async def setprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setprice command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "用法：/setprice <月数> <价格>\n"
            "例如：/setprice 3 5.99"
        )
        return
    
    try:
        months = int(context.args[0])
        price = float(context.args[1])
        
        if months not in [3, 6, 12]:
            await update.message.reply_text("❌ 月数必须是 3、6 或 12")
            return
        
        db.set_price(months, price)
        await update.message.reply_text(f"✅ 已设置 {months} 个月价格为 ${price:.2f} USDT")
        
    except ValueError:
        await update.message.reply_text("❌ 参数格式错误")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    await update.message.reply_text(
        "ℹ️ <b>Fragment 余额查询</b>\n\n"
        "⚠️ Fragment API 不提供余额查询接口\n\n"
        "💡 <b>建议：</b>\n"
        "• 直接在浏览器访问 fragment.com 查看余额\n"
        "• 确保 Fragment 账户有足够余额用于会员开通",
        parse_mode='HTML'
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command - initialize Fragment with manual authentication"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    await update.message.reply_text(
        "🔐 <b>Fragment 认证配置</b>\n\n"
        "本项目使用<b>手动认证方式</b>，避免账号冻结风险\n\n"
        "📝 <b>配置步骤：</b>\n\n"
        "1️⃣ 在浏览器访问 https://fragment.com 并登录\n"
        "2️⃣ 打开开发者工具（F12）\n"
        "3️⃣ 从 Application > Cookies 获取：\n"
        "   • stel_ssid\n"
        "   • stel_token\n"
        "   • stel_dt\n"
        "4️⃣ 从 Network 请求中获取 hash 参数\n"
        "5️⃣ 填入服务器上的 fragment_auth.json 文件\n\n"
        "✅ <b>优势：</b>\n"
        "• 无需验证码，只需浏览器点击确认\n"
        "• 避免账号冻结风险\n"
        "• 认证数据长期有效\n"
        "• 配置简单，更加安全\n\n"
        "📚 详细教程请参考项目 README.md",
        parse_mode='HTML'
    )
    
    # Try to check if already configured
    try:
        success = await fragment._ensure_initialized()
        
        if success:
            await update.message.reply_text(
                "✅ <b>Fragment 已配置且连接正常！</b>\n\n"
                "🎉 Fragment API 已就绪\n"
                "💎 现在可以自动开通 Premium 会员了\n\n"
                "💡 <b>提示：</b>\n"
                "• 认证数据已加载\n"
                "• 如需更新配置，修改 fragment_auth.json 并重启机器人",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ <b>Fragment 未配置或配置错误</b>\n\n"
                "<b>请按上述步骤配置 fragment_auth.json</b>\n\n"
                "配置文件示例：\n"
                "<code>fragment_auth.json.example</code>\n\n"
                "配置完成后重启机器人即可生效",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Exception in login_command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>检查配置时发生异常</b>\n\n"
            f"<b>错误类型：</b> {type(e).__name__}\n"
            f"<b>错误信息：</b> {str(e)[:200]}\n\n"
            f"<b>建议操作：</b>\n"
            f"• 检查 Telethon 是否正确安装\n"
            f"• 确认 .env 配置正确\n"
            f"• 查看完整日志获取更多信息",
            parse_mode='HTML'
        )

# ============================================================================
# CALLBACK QUERY HANDLERS
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Log callback query at INFO level for observability
    logger.info(f"📱 Callback Query: user_id={user.id}, username={user.username}, data={data}")
    
    utils.log_user_action(user.id, f"Callback: {data}")
    
    # Main menu navigation
    if data == "back_to_main":
        await show_main_menu(query, user)
    
    elif data == "menu_buy_premium":
        await show_buy_premium(query)
    
    elif data == "menu_buy_stars":
        await show_buy_stars(query)
    
    elif data == "menu_user_center":
        await show_user_center(query, user)
    
    elif data == "menu_my_orders":
        await show_user_orders(query, user)
    
    elif data == "menu_recharge":
        await show_recharge(query)
    
    # Premium purchase flow
    elif data.startswith("buy_premium_"):
        months = int(data.split("_")[2])
        await show_purchase_type(query, months)
    
    elif data.startswith("purchase_self_"):
        months = int(data.split("_")[2])
        await handle_self_purchase(query, user, months)
    
    elif data.startswith("purchase_gift_"):
        months = int(data.split("_")[2])
        await handle_gift_purchase_start(query, user, months)
    
    # Stars purchase flow
    elif data.startswith("buy_stars_"):
        stars = int(data.split("_")[2])
        await handle_stars_purchase(query, user, stars)
    
    # Gift confirmation flow
    elif data.startswith("confirm_gift_"):
        order_data = data.split("_", 2)[2]
        await handle_gift_confirmation(query, user, order_data)
    
    elif data == "cancel_gift":
        await handle_gift_cancellation(query, user)
    
    # Recharge confirmation flow
    elif data.startswith("confirm_recharge_"):
        amount_str = data.split("_", 2)[2]
        await handle_recharge_confirmation(query, user, float(amount_str))
    
    elif data == "cancel_recharge":
        await handle_recharge_cancellation(query, user)
    
    # Payment actions
    elif data.startswith("paid_"):
        order_id = data.split("_", 1)[1]
        await verify_payment(query, order_id)
    
    elif data.startswith("cancel_"):
        order_id = data.split("_", 1)[1]
        await cancel_order(query, order_id)
    
    # Order details
    elif data.startswith("order_detail_"):
        order_id = data.split("_", 2)[2]
        await show_order_details(query, order_id)
    
    # Order pagination
    elif data.startswith("orders_page_"):
        page = int(data.split("_")[2])
        await show_user_orders(query, user, page)
    
    # Admin panel
    elif data == "admin_panel":
        await show_admin_panel(query, user)
    
    elif data == "admin_balance":
        await admin_check_balance(query, user)
    
    elif data == "admin_stats":
        await show_admin_stats(query, user)
    
    elif data == "admin_stats_orders":
        await show_admin_stats_orders(query, user)
    
    elif data == "admin_stats_income":
        await show_admin_stats_income(query, user)
    
    elif data == "admin_stats_users":
        await show_admin_stats_users(query, user)
    
    elif data == "admin_login":
        await admin_login(query, user)
    
    elif data == "admin_prices":
        await show_admin_prices(query, user)
    
    elif data == "admin_orders":
        await show_admin_orders(query, user)
    
    # Back navigation
    elif data == "back_to_buy":
        await show_buy_premium(query)
    
    elif data == "cancel_operation":
        db.clear_user_state(user.id)
        await query.edit_message_text(
            messages.get_cancel_message(),
            reply_markup=keyboards.get_back_to_main_keyboard()
        )
    
    # Unknown callback
    else:
        logger.warning(f"Unknown callback data: {data}")
        await query.answer("⚠️ 此功能暂未实现", show_alert=True)

# ============================================================================
# MENU DISPLAY FUNCTIONS
# ============================================================================

async def show_main_menu(query, user):
    """Show main menu"""
    welcome_message = messages.get_welcome_message(user.first_name, is_admin(user.id))
    keyboard = keyboards.get_main_menu_keyboard()
    
    try:
        await query.edit_message_text(
            welcome_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
        await query.message.reply_text(
            welcome_message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

async def show_buy_premium(query):
    """Show Premium purchase page"""
    prices = db.get_prices()
    message = messages.get_buy_premium_message(prices)
    keyboard = keyboards.get_premium_packages_keyboard(prices)
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_buy_stars(query):
    """Show Stars purchase page"""
    prices = db.get_stars_prices()
    message = messages.get_buy_stars_message(prices)
    keyboard = keyboards.get_stars_packages_keyboard(prices)
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_user_center(query, user):
    """Show user center with statistics"""
    stats = db.get_user_statistics(user.id)
    message = messages.get_user_center_message(user.id, user.username, stats)
    keyboard = keyboards.get_user_center_keyboard()
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_user_orders(query, user, page=1):
    """Show user's orders with pagination"""
    orders_per_page = 5
    all_orders = db.get_user_orders(user.id)
    
    total_orders = len(all_orders)
    total_pages = (total_orders + orders_per_page - 1) // orders_per_page
    
    start_idx = (page - 1) * orders_per_page
    end_idx = start_idx + orders_per_page
    page_orders = all_orders[start_idx:end_idx]
    
    message = messages.get_orders_list_message(page_orders, page, total_pages)
    keyboard = keyboards.get_orders_pagination_keyboard(page, total_pages, user.id)
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_recharge(query):
    """Show recharge page"""
    user = query.from_user
    
    # Get current balance
    balance = db.get_user_balance(user.id)
    
    message = messages.get_recharge_message()
    message = f"💰 当前余额：${balance:.2f} USDT\n\n" + message
    
    keyboard = keyboards.get_cancel_keyboard()
    
    # Set user state to awaiting recharge amount
    db.set_user_state(user.id, 'awaiting_recharge_amount', {})
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_purchase_type(query, months):
    """Show purchase type selection (self or gift)"""
    prices = db.get_prices()
    price = prices[months]
    
    message = messages.get_purchase_type_message(months, price)
    keyboard = keyboards.get_purchase_type_keyboard(months)
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

# ============================================================================
# PURCHASE HANDLERS
# ============================================================================

async def fulfill_order_immediately(bot, order, user_id: int, chat_id: int):
    """
    Fulfill an order immediately (used for balance-only purchases)
    
    Args:
        bot: Bot instance
        order: Order dict
        user_id: User ID
        chat_id: Chat ID for notifications
        
    Returns:
        bool: True if fulfilled successfully
    """
    try:
        order_id = order['order_id']
        product_type = order['product_type']
        
        if product_type == PRODUCT_TYPE_PREMIUM:
            # Determine recipient
            recipient_id = order.get('recipient_id') or user_id
            recipient_username = order.get('recipient_username')
            
            # If we only have username, try to resolve to ID using Telethon
            if not recipient_id and recipient_username:
                logger.info(f"Attempting Telethon resolution for recipient @{recipient_username}")
                try:
                    resolver = await get_resolver()
                    if resolver:
                        telethon_info = await resolver.resolve_username(recipient_username)
                        if telethon_info:
                            recipient_id = telethon_info['user_id']
                            logger.info(f"✅ Telethon resolved @{recipient_username} to user_id {recipient_id}")
                        else:
                            logger.warning(f"Telethon could not resolve @{recipient_username}")
                except Exception as e:
                    logger.warning(f"Error during Telethon resolution: {e}")
            
            # If still no recipient_id, use buyer's ID as fallback
            if not recipient_id:
                logger.warning(f"No recipient_id available for order {order_id}, using buyer's ID")
                recipient_id = user_id
            
            # Gift Premium
            logger.info(f"Attempting to gift {order['months']} months Premium to user {recipient_id}")
            success = await fragment.gift_premium(recipient_id, order['months'])
            
            if success:
                db.update_order_status(order_id, 'completed')
                logger.info(f"✅ Order {order_id} completed successfully")
                
                # Create gift record if applicable
                if order.get('recipient_id') or order.get('recipient_username'):
                    db.create_gift_record(
                        order_id,
                        user_id,
                        recipient_id,
                        PRODUCT_TYPE_PREMIUM,
                        order['months']
                    )
                
                # Send success message
                success_msg = f"✅ 订单完成！\n\n💎 {order['months']} 个月 Telegram Premium 已开通！\n"
                if order.get('balance_to_use', 0) > 0:
                    success_msg += f"💰 使用余额：${order['balance_to_use']:.4f}\n"
                
                if recipient_username:
                    success_msg += f"🎁 已赠送给：@{recipient_username}\n"
                elif order.get('recipient_id') and order.get('recipient_id') != user_id:
                    success_msg += f"🎁 已赠送给：User ID {order['recipient_id']}\n"
                
                success_msg += "\n感谢您的购买！"
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=success_msg,
                    parse_mode='Markdown'
                )
                utils.log_order_action(order_id, "Completed", "Premium gifted (balance payment)")
                return True
            else:
                # Keep order as 'paid' for manual retry
                retry_count = db.update_order_status(order_id, 'paid', error=ERROR_MSG_FRAGMENT_GIFTING_FAILED)
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ 订单已创建，但 Premium 开通遇到问题。\n\n管理员将尽快处理。\n订单号：`{order_id}`",
                    parse_mode='Markdown'
                )
                utils.log_order_action(order_id, "Paid-NeedsRetry", f"Premium gifting failed, attempt {retry_count}")
                return False
                
        elif product_type == PRODUCT_TYPE_STARS:
            # Mark stars as completed
            db.update_order_status(order_id, 'completed')
            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ 订单完成！\n\n⭐ {order['product_quantity']} Telegram Stars 已充值！\n"
                     f"💰 使用余额：${order.get('balance_to_use', 0):.4f}\n\n"
                     f"感谢您的购买！",
                parse_mode='Markdown'
            )
            utils.log_order_action(order_id, "Completed", f"{order['product_quantity']} stars (balance payment)")
            return True
            
        elif product_type == PRODUCT_TYPE_RECHARGE:
            # This shouldn't happen (recharge doesn't use balance)
            logger.error(f"Recharge order {order_id} should not use balance payment")
            return False
        
        return False
        
    except Exception as e:
        logger.error(f"Error fulfilling order {order['order_id']}: {e}", exc_info=True)
        return False

async def handle_self_purchase(query, user, months):
    """Handle purchase for self with balance-first strategy"""
    prices = db.get_prices()
    base_price = prices[months]
    
    # Check user balance
    user_balance = db.get_user_balance(user.id)
    
    # Create order
    order_id = str(uuid.uuid4())
    product_name = utils.get_product_name(PRODUCT_TYPE_PREMIUM, months=months)
    
    if user_balance >= base_price:
        # Full payment from balance
        logger.info(f"User {user.id} has sufficient balance (${user_balance:.4f}) for ${base_price:.2f}")
        
        # Deduct balance immediately
        new_balance = db.update_user_balance(user.id, base_price, operation='subtract')
        
        if new_balance is not None:
            # Create order with balance payment
            db.create_order(
                order_id=order_id,
                user_id=user.id,
                months=months,
                price=base_price,
                product_type=PRODUCT_TYPE_PREMIUM,
                balance_to_use=base_price,
                remaining_amount=0.0
            )
            
            # Mark as paid immediately
            db.update_order_status(order_id, 'paid')
            
            # Send processing message
            await query.edit_message_text(
                f"⚙️ 正在处理您的订单...\n\n"
                f"💰 已扣除余额：${base_price:.2f}\n"
                f"💳 剩余余额：${new_balance:.4f}"
            )
            
            # Fulfill immediately
            order = db.get_order(order_id)
            bot_instance = query.get_bot()
            success = await fulfill_order_immediately(bot_instance, order, user.id, query.message.chat_id)
            
            utils.log_order_action(order_id, "Created-BalancePaid", f"User {user.id}, {months} months, balance: ${base_price:.2f}")
        else:
            await query.answer("❌ 余额扣除失败，请重试", show_alert=True)
            
    elif user_balance > 0:
        # Partial payment from balance
        balance_to_use = user_balance
        remaining_amount = base_price - balance_to_use
        unique_remaining = utils.generate_unique_price(remaining_amount)
        
        logger.info(f"User {user.id} using partial balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
        
        # Create order with partial balance (don't deduct yet)
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=months,
            price=base_price,
            product_type=PRODUCT_TYPE_PREMIUM,
            balance_to_use=balance_to_use,
            remaining_amount=unique_remaining
        )
        
        # Show payment info for remaining amount
        await send_payment_info(query, order_id, product_name, unique_remaining, user.id, 
                               balance_info=f"💰 将使用余额：${balance_to_use:.4f}\n📊 需链上支付：${unique_remaining:.4f}")
        
        utils.log_order_action(order_id, "Created-PartialBalance", 
                              f"User {user.id}, {months} months, balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
    else:
        # No balance, full payment on-chain
        price = utils.generate_unique_price(base_price)
        
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=months,
            price=price,
            product_type=PRODUCT_TYPE_PREMIUM,
            balance_to_use=0.0,
            remaining_amount=price
        )
        
        await send_payment_info(query, order_id, product_name, price, user.id)
        
        utils.log_order_action(order_id, "Created", f"User {user.id}, {months} months, ${price:.4f}")

async def handle_gift_purchase_start(query, user, months):
    """Start gift purchase flow - ask for recipient"""
    # Save state
    db.set_user_state(user.id, 'awaiting_recipient', {'months': months})
    
    message = """
🎁 **赠送 Premium 给好友**

请输入对方的信息：
• @username （例如：@johndoe）
• 或者 User ID （例如：123456789）

💡 提示：
• 可以在对方的个人资料中找到 username
• User ID 可通过 @userinfobot 获取

输入完成后按发送，或点击下方取消按钮
"""
    
    keyboard = keyboards.get_cancel_keyboard()
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def handle_stars_purchase(query, user, stars):
    """Handle stars purchase with balance-first strategy"""
    prices = db.get_stars_prices()
    base_price = prices.get(stars, stars * 0.01)
    
    # Check user balance
    user_balance = db.get_user_balance(user.id)
    
    # Create order
    order_id = str(uuid.uuid4())
    product_name = utils.get_product_name(PRODUCT_TYPE_STARS, stars=stars)
    
    if user_balance >= base_price:
        # Full payment from balance
        logger.info(f"User {user.id} has sufficient balance (${user_balance:.4f}) for ${base_price:.2f}")
        
        # Deduct balance immediately
        new_balance = db.update_user_balance(user.id, base_price, operation='subtract')
        
        if new_balance is not None:
            # Create order with balance payment
            db.create_order(
                order_id=order_id,
                user_id=user.id,
                months=0,
                price=base_price,
                product_type=PRODUCT_TYPE_STARS,
                product_quantity=stars,
                balance_to_use=base_price,
                remaining_amount=0.0
            )
            
            # Mark as paid and completed immediately
            db.update_order_status(order_id, 'paid')
            db.update_order_status(order_id, 'completed')
            
            # Send success message
            await query.edit_message_text(
                f"✅ 订单完成！\n\n"
                f"⭐ {stars} Telegram Stars 已充值！\n"
                f"💰 已扣除余额：${base_price:.2f}\n"
                f"💳 剩余余额：${new_balance:.4f}\n\n"
                f"感谢您的购买！"
            )
            
            utils.log_order_action(order_id, "Completed-BalancePaid", f"User {user.id}, {stars} stars, balance: ${base_price:.2f}")
        else:
            await query.answer("❌ 余额扣除失败，请重试", show_alert=True)
            
    elif user_balance > 0:
        # Partial payment from balance
        balance_to_use = user_balance
        remaining_amount = base_price - balance_to_use
        unique_remaining = utils.generate_unique_price(remaining_amount)
        
        logger.info(f"User {user.id} using partial balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
        
        # Create order with partial balance (don't deduct yet)
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=0,
            price=base_price,
            product_type=PRODUCT_TYPE_STARS,
            product_quantity=stars,
            balance_to_use=balance_to_use,
            remaining_amount=unique_remaining
        )
        
        # Show payment info for remaining amount
        await send_payment_info(query, order_id, product_name, unique_remaining, user.id,
                               balance_info=f"💰 将使用余额：${balance_to_use:.4f}\n📊 需链上支付：${unique_remaining:.4f}")
        
        utils.log_order_action(order_id, "Created-PartialBalance",
                              f"User {user.id}, {stars} stars, balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
    else:
        # No balance, full payment on-chain
        price = utils.generate_unique_price(base_price)
        
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=0,
            price=price,
            product_type=PRODUCT_TYPE_STARS,
            product_quantity=stars,
            balance_to_use=0.0,
            remaining_amount=price
        )
        
        await send_payment_info(query, order_id, product_name, price, user.id)
        
        utils.log_order_action(order_id, "Created", f"User {user.id}, {stars} stars, ${price:.4f}")

async def handle_gift_confirmation(query, user, order_data):
    """Handle gift purchase confirmation with balance-first strategy"""
    import json
    import base64
    
    try:
        # Decode order data
        order_dict = json.loads(base64.b64decode(order_data).decode())
        months = order_dict['months']
        recipient_id = order_dict.get('recipient_id')
        recipient_username = order_dict.get('recipient_username')
        
        # Get user state to verify
        user_state = db.get_user_state(user.id)
        if not user_state or user_state.get('state') != 'confirm_recipient':
            await query.answer("❌ 会话已过期，请重新开始", show_alert=True)
            return
        
        state_data = user_state.get('data', {})
        base_price = state_data.get('price')
        
        # Check user balance
        user_balance = db.get_user_balance(user.id)
        
        # Create order
        order_id = str(uuid.uuid4())
        product_name = utils.get_product_name(PRODUCT_TYPE_PREMIUM, months=months)
        
        if user_balance >= base_price:
            # Full payment from balance
            logger.info(f"User {user.id} has sufficient balance (${user_balance:.4f}) for ${base_price:.2f}")
            
            # Deduct balance immediately
            new_balance = db.update_user_balance(user.id, base_price, operation='subtract')
            
            if new_balance is not None:
                # Create order with balance payment
                db.create_order(
                    order_id=order_id,
                    user_id=user.id,
                    months=months,
                    price=base_price,
                    product_type=PRODUCT_TYPE_PREMIUM,
                    recipient_id=recipient_id,
                    recipient_username=recipient_username,
                    balance_to_use=base_price,
                    remaining_amount=0.0
                )
                
                # Mark as paid immediately
                db.update_order_status(order_id, 'paid')
                
                # Clear state
                db.clear_user_state(user.id)
                
                # Send processing message
                await query.edit_message_text(
                    f"⚙️ 正在处理您的订单...\n\n"
                    f"💰 已扣除余额：${base_price:.2f}\n"
                    f"💳 剩余余额：${new_balance:.4f}"
                )
                
                # Fulfill immediately
                order = db.get_order(order_id)
                bot_instance = query.get_bot()
                success = await fulfill_order_immediately(bot_instance, order, user.id, query.message.chat_id)
                
                utils.log_order_action(order_id, "Created-BalancePaid", f"Gift to {recipient_username or recipient_id}, balance: ${base_price:.2f}")
            else:
                await query.answer("❌ 余额扣除失败，请重试", show_alert=True)
                
        elif user_balance > 0:
            # Partial payment from balance
            balance_to_use = user_balance
            remaining_amount = base_price - balance_to_use
            unique_remaining = utils.generate_unique_price(remaining_amount)
            
            logger.info(f"User {user.id} using partial balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
            
            # Create order with partial balance (don't deduct yet)
            db.create_order(
                order_id=order_id,
                user_id=user.id,
                months=months,
                price=base_price,
                product_type=PRODUCT_TYPE_PREMIUM,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
                balance_to_use=balance_to_use,
                remaining_amount=unique_remaining
            )
            
            # Clear state
            db.clear_user_state(user.id)
            
            # Generate QR code
            payment_text = config.PAYMENT_WALLET_ADDRESS
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(payment_text)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            bio = io.BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            # Add gift recipient info
            if recipient_username:
                gift_info = f"🎁 **赠送给**：@{recipient_username}\n"
            elif recipient_id:
                gift_info = f"🎁 **赠送给**：User ID {recipient_id}\n"
            else:
                gift_info = ""
            
            balance_info = f"💰 将使用余额：${balance_to_use:.4f}\n📊 需链上支付：${unique_remaining:.4f}"
            
            message = messages.get_payment_message(
                order_id=order_id,
                product_name=product_name,
                price=unique_remaining,
                wallet_address=config.PAYMENT_WALLET_ADDRESS,
                expires_in_minutes=30
            )
            
            # Combine gift info and balance info
            combined_info = f"{gift_info}\n{balance_info}" if gift_info else balance_info
            message = combined_info + "\n\n" + message
            
            keyboard = keyboards.get_payment_keyboard(order_id)
            
            await query.message.reply_photo(
                photo=bio,
                caption=message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            # Start payment monitoring
            bot_instance = query.get_bot()
            asyncio.create_task(
                monitor_payment(bot_instance, order_id, user.id, unique_remaining, query.message.chat_id)
            )
            
            utils.log_order_action(order_id, "Created-PartialBalance", 
                                  f"Gift to {recipient_username or recipient_id}, balance: ${balance_to_use:.4f}, remaining: ${unique_remaining:.4f}")
        else:
            # No balance, full payment on-chain
            price = utils.generate_unique_price(base_price)
            
            db.create_order(
                order_id=order_id,
                user_id=user.id,
                months=months,
                price=price,
                product_type=PRODUCT_TYPE_PREMIUM,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
                balance_to_use=0.0,
                remaining_amount=price
            )
            
            # Clear state
            db.clear_user_state(user.id)
            
            # Generate QR code
            payment_text = config.PAYMENT_WALLET_ADDRESS
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(payment_text)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            bio = io.BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            # Add gift recipient info
            if recipient_username:
                gift_info = f"\n🎁 **赠送给**：@{recipient_username}\n"
            elif recipient_id:
                gift_info = f"\n🎁 **赠送给**：User ID {recipient_id}\n"
            else:
                gift_info = ""
            
            message = messages.get_payment_message(
                order_id=order_id,
                product_name=product_name,
                price=price,
                wallet_address=config.PAYMENT_WALLET_ADDRESS,
                expires_in_minutes=30
            )
            if gift_info:
                message = message.replace("💳 **付款信息**", f"{gift_info}\n💳 **付款信息**")
            
            keyboard = keyboards.get_payment_keyboard(order_id)
            
            await query.message.reply_photo(
                photo=bio,
                caption=message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            # Start payment monitoring
            bot_instance = query.get_bot()
            asyncio.create_task(
                monitor_payment(bot_instance, order_id, user.id, price, query.message.chat_id)
            )
            
            utils.log_order_action(order_id, "Gift order confirmed", f"Recipient: {recipient_username or recipient_id}")
        
        # Edit original message to show confirmation
        try:
            await query.edit_message_text("✅ 已确认，请查看下方支付信息")
        except Exception as e:
            logger.debug(f"Could not edit message: {e}")
            
    except Exception as e:
        logger.error(f"Error in handle_gift_confirmation: {e}")
        await query.answer("❌ 处理失败，请重试", show_alert=True)

async def handle_gift_cancellation(query, user):
    """Handle gift purchase cancellation"""
    db.clear_user_state(user.id)
    
    message = "❌ 已取消赠送操作\n\n使用 /start 返回主菜单"
    keyboard = keyboards.get_back_to_main_keyboard()
    
    try:
        await query.edit_message_text(message, reply_markup=keyboard)
    except Exception:
        await query.message.reply_text(message, reply_markup=keyboard)
    
    utils.log_user_action(user.id, "Gift cancelled")

async def handle_recharge_confirmation(query, user, amount):
    """Handle recharge confirmation"""
    try:
        # Verify user state
        user_state = db.get_user_state(user.id)
        if not user_state or user_state.get('state') != 'confirm_recharge':
            await query.answer("❌ 会话已过期，请重新开始", show_alert=True)
            return
        
        # Create recharge order with unique amount
        order_id = str(uuid.uuid4())
        price = utils.generate_unique_price(amount)
        product_name = f"余额充值 ${price:.4f}"
        
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=0,
            price=price,
            product_type=PRODUCT_TYPE_RECHARGE
        )
        
        # Clear state
        db.clear_user_state(user.id)
        
        # Generate QR code and send payment info
        payment_text = config.PAYMENT_WALLET_ADDRESS
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(payment_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        message = messages.get_payment_message(
            order_id=order_id,
            product_name=product_name,
            price=price,
            wallet_address=config.PAYMENT_WALLET_ADDRESS,
            expires_in_minutes=30
        )
        
        keyboard = keyboards.get_payment_keyboard(order_id)
        
        await query.message.reply_photo(
            photo=bio,
            caption=message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Start payment monitoring
        bot_instance = query.get_bot()
        asyncio.create_task(
            monitor_payment(bot_instance, order_id, user.id, price, query.message.chat_id)
        )
        
        utils.log_order_action(order_id, "Recharge order created", f"Amount: ${price:.4f}")
        
        # Edit original message
        try:
            await query.edit_message_text("✅ 已确认，请查看下方支付信息")
        except Exception as e:
            logger.debug(f"Could not edit message: {e}")
            
    except Exception as e:
        logger.error(f"Error in handle_recharge_confirmation: {e}")
        await query.answer("❌ 处理失败，请重试", show_alert=True)

async def handle_recharge_cancellation(query, user):
    """Handle recharge cancellation"""
    db.clear_user_state(user.id)
    
    message = "❌ 已取消充值操作\n\n使用 /start 返回主菜单"
    keyboard = keyboards.get_back_to_main_keyboard()
    
    try:
        await query.edit_message_text(message, reply_markup=keyboard)
    except Exception:
        await query.message.reply_text(message, reply_markup=keyboard)
    
    utils.log_user_action(user.id, "Recharge cancelled")

async def send_payment_info(query, order_id, product_name, price, user_id, balance_info=None):
    """Send payment information with QR code
    
    Args:
        balance_info: Optional balance usage info to display
    """
    # Generate QR code
    payment_text = config.PAYMENT_WALLET_ADDRESS
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(payment_text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    # Create message
    message = messages.get_payment_message(
        order_id=order_id,
        product_name=product_name,
        price=price,
        wallet_address=config.PAYMENT_WALLET_ADDRESS,
        expires_in_minutes=30
    )
    
    # Add balance info if provided
    if balance_info:
        message = balance_info + "\n\n" + message
    
    # Create keyboard
    keyboard = keyboards.get_payment_keyboard(order_id)
    
    # Send QR code and info
    await query.message.reply_photo(
        photo=bio,
        caption=message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    # Start payment monitoring
    bot_instance = query.get_bot()
    asyncio.create_task(
        monitor_payment(bot_instance, order_id, user_id, price, query.message.chat_id)
    )

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

async def fetch_recipient_info(bot, user_id=None, username=None):
    """
    Fetch recipient information from Telegram API
    Priority: text_mention > Bot API get_chat > Telethon resolver
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID (optional)
        username: Telegram username without @ (optional)
    
    Returns:
        dict: User info or None if all methods fail
    """
    try:
        # Method 1: Try Bot API get_chat
        if user_id:
            # Try to get user info by ID
            try:
                chat = await bot.get_chat(user_id)
                # Extract user information
                info = {
                    'user_id': chat.id,
                    'username': chat.username,
                    'first_name': chat.first_name,
                    'last_name': chat.last_name,
                    'photo_file_id': None
                }
                
                # Try to get profile photo
                try:
                    photos = await bot.get_user_profile_photos(chat.id, limit=1)
                    if photos.total_count > 0:
                        photo = photos.photos[0][0]
                        info['photo_file_id'] = photo.file_id
                except Exception as e:
                    logger.debug(f"Could not get profile photo: {e}")
                
                logger.info(f"✅ Bot API resolved user_id {user_id}")
                return info
                
            except Exception as e:
                logger.warning(f"Bot API could not get chat for user_id {user_id}: {e}")
                # Fall through to Telethon if username available
                
        elif username:
            # Try to get user info by username via Bot API
            try:
                chat = await bot.get_chat(f"@{username}")
                info = {
                    'user_id': chat.id,
                    'username': chat.username,
                    'first_name': chat.first_name,
                    'last_name': chat.last_name,
                    'photo_file_id': None
                }
                
                # Try to get profile photo
                try:
                    photos = await bot.get_user_profile_photos(chat.id, limit=1)
                    if photos.total_count > 0:
                        photo = photos.photos[0][0]
                        info['photo_file_id'] = photo.file_id
                except Exception as e:
                    logger.debug(f"Could not get profile photo: {e}")
                
                logger.info(f"✅ Bot API resolved username @{username}")
                return info
                
            except Exception as e:
                logger.warning(f"Bot API could not get chat for username @{username}: {e}")
                # Fall through to Telethon
        
        # Method 2: Try Telethon resolver as fallback (only for username)
        if username:
            try:
                logger.info(f"Attempting Telethon resolution for @{username}")
                resolver = await get_resolver()
                
                if resolver:
                    telethon_info = await resolver.resolve_username(username)
                    
                    if telethon_info:
                        # Convert Telethon info to our format
                        info = {
                            'user_id': telethon_info['user_id'],
                            'username': telethon_info['username'],
                            'first_name': telethon_info['first_name'],
                            'last_name': telethon_info.get('last_name', ''),
                            'photo_file_id': None  # Telethon photo bytes not compatible with Bot API
                        }
                        logger.info(f"✅ Telethon resolved @{username} to user_id {info['user_id']}")
                        return info
                else:
                    logger.info("Telethon resolver not available (not configured)")
                    
            except Exception as e:
                logger.warning(f"Telethon resolution failed for @{username}: {e}")
        
        # All methods failed
        logger.warning(f"All resolution methods failed for user_id={user_id}, username={username}")
        return None
        
    except Exception as e:
        logger.error(f"Error in fetch_recipient_info: {e}", exc_info=True)
        return None

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for recipient input, etc.)"""
    user = update.effective_user
    text = update.message.text
    message = update.message
    
    # Check if user has a state
    user_state = db.get_user_state(user.id)
    
    if not user_state:
        # No active state, ignore
        return
    
    state = user_state.get('state')
    state_data = user_state.get('data', {})
    
    if state == 'awaiting_recipient':
        # User is providing recipient info for gift
        
        # First, check if the message contains text mention entities
        recipient_id = None
        recipient_username = None
        recipient_first_name = None
        
        if message.entities:
            for entity in message.entities:
                # Check for TEXT_MENTION entity (when user is @mentioned and has privacy settings)
                if entity.type == "text_mention" and entity.user:
                    recipient_id = entity.user.id
                    recipient_username = entity.user.username
                    recipient_first_name = entity.user.first_name
                    logger.info(f"Found text_mention entity: user_id={recipient_id}, username={recipient_username}")
                    break
                # Check for MENTION entity (regular @username)
                elif entity.type == "mention":
                    # Extract username from text
                    mention_text = text[entity.offset:entity.offset + entity.length]
                    if mention_text.startswith('@'):
                        recipient_username = mention_text[1:]
                    logger.info(f"Found mention entity: username={recipient_username}")
                    break
        
        # If no entity found, fall back to parsing input
        if not recipient_id and not recipient_username:
            recipient_info = utils.parse_recipient_input(text)
            
            if recipient_info['type'] is None:
                await update.message.reply_text(
                    "❌ 无效的输入格式\n\n"
                    "**推荐方式：**\n"
                    "• 使用 @ 提及功能（会显示为蓝色链接）\n"
                    "  例如：@username\n\n"
                    "**其他方式：**\n"
                    "• 输入 User ID（例如：123456789）\n"
                    "• 转发对方的消息给我\n\n"
                    "💡 提示：使用 @ 提及时，如果显示为蓝色链接，\n"
                    "说明可以成功识别该用户！\n\n"
                    "或点击取消按钮取消操作",
                    reply_markup=keyboards.get_cancel_keyboard(),
                    parse_mode='Markdown'
                )
                return
            
            recipient_id = recipient_info['value'] if recipient_info['type'] == 'user_id' else None
            recipient_username = recipient_info['value'] if recipient_info['type'] == 'username' else None
        
        # Get months and price
        months = state_data.get('months')
        prices = db.get_prices()
        price = prices[months]
        
        # If we have recipient_id from text_mention, we can proceed directly
        if recipient_id:
            logger.info(f"Using recipient_id from text_mention: {recipient_id}")
            # Try to fetch more info from bot
            fetched_info = await fetch_recipient_info(context.bot, recipient_id, None)
            if fetched_info:
                recipient_username = fetched_info['username']
                recipient_first_name = fetched_info['first_name']
            elif not recipient_first_name:
                # If we couldn't fetch but have ID from entity, continue with what we have
                recipient_first_name = "User"
        
        # Fetch user information from Telegram
        if not recipient_id and recipient_username:
            fetched_info = await fetch_recipient_info(context.bot, None, recipient_username)
        elif recipient_id and not recipient_first_name:
            fetched_info = await fetch_recipient_info(context.bot, recipient_id, recipient_username)
        else:
            # We already have the info from entity
            fetched_info = {
                'user_id': recipient_id,
                'username': recipient_username,
                'first_name': recipient_first_name or "User",
                'photo_file_id': None
            }
        
        if fetched_info is None:
            # If we have a username but couldn't fetch info, offer to proceed anyway
            if recipient_username and not recipient_id:
                logger.info(f"Could not fetch info for @{recipient_username}, offering to proceed with username only")
                
                # Show option to proceed with username only
                error_msg = (
                    "⚠️ **无法验证收礼人信息**\n\n"
                    "**关于 @username 验证：**\n"
                    "由于 Telegram Bot API 和 Telethon 的限制，无法验证该用户。\n\n"
                    "**您可以选择：**\n\n"
                    "1️⃣ **继续使用 @username**\n"
                    "   • 我们会记录 username\n"
                    "   • 支付后会尝试再次解析\n"
                    "   • 如果解析成功，会员将正常开通\n\n"
                    "2️⃣ **重新输入其他方式**\n"
                    "   • 使用 @ 提及功能（显示为蓝色链接）\n"
                    "   • 转发对方的消息给我\n"
                    "   • 获取对方的 User ID（数字格式）\n\n"
                )
                
                # Update state to allow confirmation with username only
                db.set_user_state(user.id, 'confirm_recipient', {
                    'months': months,
                    'price': price,
                    'recipient_id': None,
                    'recipient_username': recipient_username,
                    'recipient_info': {
                        'user_id': None,
                        'username': recipient_username,
                        'first_name': f"@{recipient_username}",
                        'last_name': '',
                        'photo_file_id': None
                    }
                })
                
                # Show confirmation with username only
                confirmation_message = f"""
🎁 **确认赠送信息**

📦 商品：{months}个月 Telegram Premium
💰 价格：${price:.2f} USDT

👤 **收礼人**：@{recipient_username}
⚠️ **提示**：无法验证该用户，但仍可继续

━━━━━━━━━━━━━━
📌 支付后我们会再次尝试解析该用户
如果成功，会员将自动开通
"""
                
                # Encode order data
                import json
                import base64
                order_data_dict = {
                    'months': months,
                    'recipient_id': None,
                    'recipient_username': recipient_username
                }
                order_data = base64.b64encode(json.dumps(order_data_dict).encode()).decode()
                
                keyboard = keyboards.get_gift_confirmation_keyboard(order_data)
                
                await update.message.reply_text(
                    confirmation_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return
            
            # For other cases (no username, or user_id failed), show error
            error_msg = "❌ 无法获取收礼人信息\n\n"
            if recipient_id:
                error_msg += (
                    "**可能的原因：**\n"
                    "• User ID 不正确\n"
                    "• 该用户尚未与 Bot 交互\n"
                    "• 用户隐私设置限制\n\n"
                    "**解决方法：**\n"
                    "• 让对方先发送 /start 给本 Bot\n"
                    "• 确认 User ID 是否正确\n"
                    "• 或尝试转发对方的消息给我\n\n"
                )
            
            error_msg += "请检查后重新输入，或点击取消按钮"
            
            await update.message.reply_text(
                error_msg,
                reply_markup=keyboards.get_cancel_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        # Update state to confirm_recipient with all details
        db.set_user_state(user.id, 'confirm_recipient', {
            'months': months,
            'price': price,
            'recipient_id': fetched_info.get('user_id'),
            'recipient_username': fetched_info.get('username'),
            'recipient_info': fetched_info
        })
        
        # Show confirmation page
        confirmation_message = messages.get_gift_confirmation_message(fetched_info, months, price)
        
        # Encode order data for callback
        import json
        import base64
        order_data_dict = {
            'months': months,
            'recipient_id': fetched_info.get('user_id'),
            'recipient_username': fetched_info.get('username')
        }
        order_data = base64.b64encode(json.dumps(order_data_dict).encode()).decode()
        
        keyboard = keyboards.get_gift_confirmation_keyboard(order_data)
        
        # If recipient has profile photo, send it with the message
        if fetched_info.get('photo_file_id'):
            try:
                await update.message.reply_photo(
                    photo=fetched_info['photo_file_id'],
                    caption=confirmation_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not send photo: {e}")
                await update.message.reply_text(
                    confirmation_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                confirmation_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
    
    elif state == 'awaiting_recharge_amount':
        # User is providing recharge amount
        try:
            amount = float(text.strip())
            
            # Validate amount
            if amount < 5:
                await update.message.reply_text(
                    "❌ 充值金额不能低于 5 USDT\n\n请重新输入",
                    reply_markup=keyboards.get_cancel_keyboard()
                )
                return
            
            if amount > 1000:
                await update.message.reply_text(
                    "❌ 单次充值金额不能超过 1000 USDT\n\n请重新输入",
                    reply_markup=keyboards.get_cancel_keyboard()
                )
                return
            
            # Update state to confirm recharge
            db.set_user_state(user.id, 'confirm_recharge', {'amount': amount})
            
            # Show confirmation
            confirmation_message = messages.get_recharge_confirmation_message(amount)
            keyboard = keyboards.get_recharge_confirmation_keyboard(amount)
            
            await update.message.reply_text(
                confirmation_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的金额格式\n\n"
                "请输入数字金额（例如：10 或 50.5）\n"
                "或点击取消按钮",
                reply_markup=keyboards.get_cancel_keyboard()
            )

# ============================================================================
# PAYMENT MONITORING
# ============================================================================

async def monitor_payment(bot, order_id: str, user_id: int, amount: float, chat_id: int):
    """Monitor for payment in background"""
    try:
        logger.info(f"Monitoring payment for order {order_id}")
        
        # Wait for payment
        payment_info = await tron_payment.check_payment(amount, config.PAYMENT_TIMEOUT)
        
        if payment_info:
            tx_hash = payment_info['tx_hash']
            
            # Verify USDT authenticity
            is_authentic = await tron_payment.verify_usdt_authenticity(tx_hash)
            
            if not is_authentic:
                db.update_order_status(order_id, 'failed')
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ 检测到假 USDT！\n交易已拒绝，请使用真实的 USDT 进行支付。"
                )
                utils.log_payment_action(tx_hash, "Rejected", "Fake USDT detected")
                return
            
            # Record transaction
            db.create_transaction(
                tx_hash,
                order_id,
                payment_info['amount'],
                payment_info['from']
            )
            
            # Get order details
            order = db.get_order(order_id)
            
            # Deduct balance if this order uses partial balance
            balance_to_use = order.get('balance_to_use', 0.0)
            if balance_to_use > 0:
                logger.info(f"Deducting balance ${balance_to_use:.4f} for order {order_id}")
                new_balance = db.update_user_balance(user_id, balance_to_use, operation='subtract')
                if new_balance is None:
                    logger.error(f"Failed to deduct balance for order {order_id}")
                    await bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ 链上支付已确认，但余额扣除失败。请联系管理员。"
                    )
                    # Still proceed with fulfillment
                else:
                    logger.info(f"Balance deducted, new balance: ${new_balance:.4f}")
            
            # Update order status
            db.update_order_status(order_id, 'paid', tx_hash)
            utils.log_payment_action(tx_hash, "Verified", f"Order {order_id}")
            
            # Determine recipient
            recipient_id = order.get('recipient_id') or user_id
            recipient_username = order.get('recipient_username')
            
            # If we only have username, try to resolve to ID using Telethon
            if not recipient_id and recipient_username:
                logger.info(f"Attempting Telethon resolution for recipient @{recipient_username}")
                try:
                    resolver = await get_resolver()
                    if resolver:
                        telethon_info = await resolver.resolve_username(recipient_username)
                        if telethon_info:
                            recipient_id = telethon_info['user_id']
                            logger.info(f"✅ Telethon resolved @{recipient_username} to user_id {recipient_id}")
                except Exception as e:
                    logger.warning(f"Error during Telethon resolution: {e}")
            
            # If still no recipient_id, use buyer's ID as fallback
            if not recipient_id:
                logger.warning(f"No recipient_id available for order {order_id}, using buyer's ID")
                recipient_id = user_id
            
            # Process based on product type
            if order['product_type'] == PRODUCT_TYPE_PREMIUM:
                # Send Premium
                success = await fragment.gift_premium(recipient_id, order['months'])
                
                if success:
                    db.update_order_status(order_id, 'completed')
                    
                    # Create gift record if applicable
                    if order.get('recipient_id') or order.get('recipient_username'):
                        db.create_gift_record(
                            order_id,
                            user_id,
                            recipient_id,
                            PRODUCT_TYPE_PREMIUM,
                            order['months']
                        )
                    
                    success_msg = f"✅ 支付成功！\n\n💎 {order['months']} 个月 Telegram Premium 已开通！\n"
                    
                    if balance_to_use > 0:
                        success_msg += f"💰 使用余额：${balance_to_use:.4f}\n"
                        success_msg += f"💳 链上支付：${order.get('remaining_amount', 0):.4f}\n"
                    
                    if order.get('recipient_username'):
                        success_msg += f"🎁 已赠送给：@{order['recipient_username']}\n"
                    elif order.get('recipient_id') and order.get('recipient_id') != user_id:
                        success_msg += f"🎁 已赠送给：User ID {order['recipient_id']}\n"
                    
                    success_msg += f"\n📝 交易哈希：`{tx_hash}`\n\n感谢您的购买！"
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=success_msg,
                        parse_mode='Markdown'
                    )
                    utils.log_order_action(order_id, "Completed", "Premium gifted successfully")
                else:
                    # Keep order as 'paid' for manual retry, track error
                    retry_count = db.update_order_status(order_id, 'paid', error=ERROR_MSG_FRAGMENT_GIFTING_FAILED)
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"⚠️ 支付已确认，但 Premium 开通遇到问题。\n\n"
                            f"**可能原因：**\n"
                            f"• Fragment 服务暂时不可用\n"
                            f"• 账号验证失败\n"
                            f"• 网络连接问题\n\n"
                            f"**订单状态：**\n"
                            f"• 订单号：`{order_id}`\n"
                            f"• 状态：已支付，待处理\n"
                            f"• 尝试次数：{retry_count}\n\n"
                            f"管理员可以稍后重试开通。\n"
                            f"如有疑问，请联系客服。"
                        ),
                        parse_mode='Markdown'
                    )
                    utils.log_order_action(order_id, "Paid-NeedsRetry", f"Premium gifting failed, attempt {retry_count}")
            
            elif order['product_type'] == PRODUCT_TYPE_STARS:
                # Mark as completed
                db.update_order_status(order_id, 'completed')
                
                success_msg = f"✅ 支付成功！\n\n⭐ {order['product_quantity']} Telegram Stars 已充值！\n"
                if balance_to_use > 0:
                    success_msg += f"💰 使用余额：${balance_to_use:.4f}\n"
                    success_msg += f"💳 链上支付：${order.get('remaining_amount', 0):.4f}\n"
                success_msg += f"📝 交易哈希：`{tx_hash}`\n\n感谢您的购买！"
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=success_msg,
                    parse_mode='Markdown'
                )
                utils.log_order_action(order_id, "Completed", f"{order['product_quantity']} stars")
            
            elif order['product_type'] == PRODUCT_TYPE_RECHARGE:
                # Handle balance recharge
                new_balance = db.update_user_balance(user_id, order['price'], operation='add')
                
                if new_balance is not None:
                    db.update_order_status(order_id, 'completed')
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ 充值成功！\n\n"
                             f"💰 充值金额：${order['price']:.4f} USDT\n"
                             f"💳 当前余额：${new_balance:.4f} USDT\n"
                             f"📝 交易哈希：`{tx_hash}`\n\n"
                             f"余额可用于购买会员和星星！",
                        parse_mode='Markdown'
                    )
                    utils.log_order_action(order_id, "Completed", f"Recharge ${order['price']:.4f}")
                else:
                    db.update_order_status(order_id, 'failed')
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ 支付已确认，但充值失败。\n请联系管理员处理，订单号：`{order_id}`",
                        parse_mode='Markdown'
                    )
                    utils.log_order_action(order_id, "Failed", "Balance update failed")
        
        else:
            # Payment timeout
            order = db.get_order(order_id)
            if order['status'] == 'pending':
                db.update_order_status(order_id, 'expired')
                await bot.send_message(
                    chat_id=chat_id,
                    text="⏰ 订单已超时\n\n未检测到付款，订单已自动取消。\n如需购买，请重新下单。"
                )
                utils.log_order_action(order_id, "Expired", "Payment timeout")
    
    except Exception as e:
        logger.error(f"Error monitoring payment for order {order_id}: {e}")
        utils.log_order_action(order_id, "Error", str(e))

async def verify_payment(query, order_id: str):
    """Manually verify payment when user clicks 'I have paid'"""
    # Immediate feedback to user
    try:
        await query.answer("🔍 正在验证支付，请稍候...", show_alert=False)
    except Exception as e:
        logger.debug(f"Could not send answer callback: {e}")
    
    logger.info(f"Manual payment verification requested for order: {order_id}")
    
    order = db.get_order(order_id)
    
    if not order:
        logger.warning(f"Order not found: {order_id}")
        await query.edit_message_text("❌ 订单不存在")
        return
    
    if order['status'] != 'pending':
        status_text = ORDER_STATUS.get(order['status'], order['status'])
        logger.info(f"Order {order_id} status is already: {order['status']}")
        await query.edit_message_text(f"订单状态：{status_text}")
        return
    
    logger.debug(f"Order details - ID: {order_id}, Price: ${order['price']:.4f}, Type: {order['product_type']}")
    
    # Get the amount to check for (remaining_amount if using balance, otherwise price)
    amount_to_check = order.get('remaining_amount', order['price'])
    
    await safe_edit_message(
        query.message,
        text="🔍 正在验证支付...\n\n这可能需要几分钟，请稍候。\n我们会在验证完成后通知您。"
    )
    
    # Check for recent transactions
    try:
        logger.debug(f"Fetching recent transactions for wallet: {config.PAYMENT_WALLET_ADDRESS}")
        transactions = await tron_payment.get_account_transactions(config.PAYMENT_WALLET_ADDRESS, 50)
        
        if not transactions:
            logger.warning(f"No transactions returned from TronGrid API")
            await query.message.reply_text(
                "⚠️ 无法获取交易记录\n\n"
                "可能的原因：\n"
                "1. 区块链网络延迟\n"
                "2. API 临时不可用\n\n"
                "请稍后重试，或联系管理员。"
            )
            return
        
        logger.info(f"Checking {len(transactions)} recent transactions for order {order_id}, looking for ${amount_to_check:.4f}")
        
        if transactions:
            for tx in transactions:
                # Check if amount matches (precise to 4 decimals)
                tx_amount = float(tx.get('value', 0)) / (10 ** tx.get('token_info', {}).get('decimals', 6))
                
                logger.debug(f"Checking TX {tx.get('transaction_id', '')[:8]}... - Amount: ${tx_amount:.4f} vs Expected: ${amount_to_check:.4f}")
                
                # Use tighter tolerance for unique amounts (0.00001 = 1/100 of smallest increment)
                if abs(tx_amount - amount_to_check) < 0.00001:
                    tx_hash = tx.get('transaction_id')
                    logger.info(f"Found matching transaction: {tx_hash}")
                    
                    # Check if transaction already recorded
                    existing_tx = db.get_transaction(tx_hash)
                    if existing_tx:
                        logger.info(f"Transaction {tx_hash} already recorded")
                        continue
                    
                    # Verify authenticity
                    logger.debug(f"Verifying USDT authenticity for {tx_hash}")
                    is_authentic = await tron_payment.verify_usdt_authenticity(tx_hash)
                    if not is_authentic:
                        logger.warning(f"Fake USDT detected in transaction {tx_hash}")
                        await query.message.reply_text(
                            "❌ 检测到假 USDT！\n\n"
                            "请使用真实的 USDT TRC20 代币进行支付。\n"
                            "合约地址应为：TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
                        )
                        db.update_order_status(order_id, 'failed')
                        utils.log_order_action(order_id, "Failed", "Fake USDT detected")
                        return
                    
                    # Deduct balance if this order uses partial balance
                    balance_to_use = order.get('balance_to_use', 0.0)
                    if balance_to_use > 0:
                        logger.info(f"Deducting balance ${balance_to_use:.4f} for order {order_id}")
                        new_balance = db.update_user_balance(order['user_id'], balance_to_use, operation='subtract')
                        if new_balance is None:
                            logger.error(f"Failed to deduct balance for order {order_id}")
                            await query.message.reply_text("⚠️ 链上支付已确认，但余额扣除失败。请联系管理员。")
                            # Still proceed with fulfillment
                        else:
                            logger.info(f"Balance deducted, new balance: ${new_balance:.4f}")
                    
                    # Record transaction
                    logger.info(f"Recording transaction {tx_hash} for order {order_id}")
                    db.create_transaction(tx_hash, order_id, tx_amount, tx.get('from'))
                    db.update_order_status(order_id, 'paid', tx_hash)
                    utils.log_payment_action(tx_hash, "Verified", f"Order {order_id}")
                    
                    # Determine recipient
                    recipient_id = order.get('recipient_id') or order['user_id']
                    recipient_username = order.get('recipient_username')
                    
                    # If we only have username, try to resolve to ID using Telethon
                    if not recipient_id and recipient_username:
                        logger.info(f"Attempting Telethon resolution for recipient @{recipient_username}")
                        try:
                            resolver = await get_resolver()
                            if resolver:
                                telethon_info = await resolver.resolve_username(recipient_username)
                                if telethon_info:
                                    recipient_id = telethon_info['user_id']
                                    logger.info(f"✅ Telethon resolved @{recipient_username} to user_id {recipient_id}")
                        except Exception as e:
                            logger.warning(f"Error during Telethon resolution: {e}")
                    
                    # If still no recipient_id, use buyer's ID as fallback
                    if not recipient_id:
                        logger.warning(f"No recipient_id available for order {order_id}, using buyer's ID")
                        recipient_id = order['user_id']
                    
                    # Gift Premium or Stars
                    if order['product_type'] == PRODUCT_TYPE_PREMIUM:
                        logger.info(f"Attempting to gift {order['months']} months Premium to user {recipient_id}")
                        success = await fragment.gift_premium(recipient_id, order['months'])
                        
                        if success:
                            db.update_order_status(order_id, 'completed')
                            logger.info(f"✅ Order {order_id} completed successfully")
                            
                            # Create gift record if applicable
                            if order.get('recipient_id') or order.get('recipient_username'):
                                db.create_gift_record(
                                    order_id,
                                    order['user_id'],
                                    recipient_id,
                                    PRODUCT_TYPE_PREMIUM,
                                    order['months']
                                )
                            
                            success_msg = f"✅ 支付验证成功！\n\n💎 {order['months']} 个月 Premium 已开通！\n"
                            if balance_to_use > 0:
                                success_msg += f"💰 使用余额：${balance_to_use:.4f}\n"
                                success_msg += f"💳 链上支付：${order.get('remaining_amount', 0):.4f}\n"
                            success_msg += "\n感谢您的购买！"
                            
                            await query.message.reply_text(success_msg)
                            utils.log_order_action(order_id, "Completed", "Premium gifted")
                        else:
                            # Keep order as 'paid' for manual retry, track error
                            retry_count = db.update_order_status(order_id, 'paid', error=ERROR_MSG_FRAGMENT_GIFTING_FAILED)
                            
                            logger.error(f"Failed to gift Premium for order {order_id}, attempt {retry_count}")
                            await query.message.reply_text(
                                f"⚠️ 支付已确认，但 Premium 开通遇到问题。\n\n"
                                f"**可能原因：**\n"
                                f"• Fragment 服务暂时不可用\n"
                                f"• 账号验证失败\n"
                                f"• 网络连接问题\n\n"
                                f"**订单状态：**\n"
                                f"• 订单号：`{order_id}`\n"
                                f"• 状态：已支付，待处理\n"
                                f"• 尝试次数：{retry_count}\n\n"
                                f"管理员可以稍后重试开通。\n"
                                f"如有疑问，请联系客服。",
                                parse_mode='Markdown'
                            )
                            utils.log_order_action(order_id, "Paid-NeedsRetry", f"Premium gifting failed, attempt {retry_count}")
                    elif order['product_type'] == PRODUCT_TYPE_STARS:
                        db.update_order_status(order_id, 'completed')
                        logger.info(f"✅ Stars order {order_id} completed")
                        
                        success_msg = f"✅ 支付验证成功！\n\n⭐ {order['product_quantity']} Stars 已充值！\n"
                        if balance_to_use > 0:
                            success_msg += f"💰 使用余额：${balance_to_use:.4f}\n"
                            success_msg += f"💳 链上支付：${order.get('remaining_amount', 0):.4f}\n"
                        success_msg += "\n感谢您的购买！"
                        
                        await query.message.reply_text(success_msg)
                        utils.log_order_action(order_id, "Completed", f"{order['product_quantity']} stars")
                    elif order['product_type'] == PRODUCT_TYPE_RECHARGE:
                        # Handle balance recharge
                        logger.info(f"Processing balance recharge for user {order['user_id']}, amount: ${order['price']:.4f}")
                        new_balance = db.update_user_balance(order['user_id'], order['price'], operation='add')
                        
                        if new_balance is not None:
                            db.update_order_status(order_id, 'completed')
                            logger.info(f"✅ Recharge order {order_id} completed, new balance: ${new_balance:.4f}")
                            await query.message.reply_text(
                                f"✅ 充值成功！\n\n"
                                f"💰 充值金额：${order['price']:.4f} USDT\n"
                                f"💳 当前余额：${new_balance:.4f} USDT\n\n"
                                f"余额可用于购买会员和星星！"
                            )
                            utils.log_order_action(order_id, "Completed", f"Recharged ${order['price']:.4f}")
                        else:
                            db.update_order_status(order_id, 'failed')
                            logger.error(f"Failed to update balance for order {order_id}")
                            await query.message.reply_text(
                                f"⚠️ 支付已确认，但充值失败。\n请联系管理员，订单号：`{order_id}`",
                                parse_mode='Markdown'
                            )
                            utils.log_order_action(order_id, "Failed", "Balance update failed")
                    return
        
        logger.info(f"No matching payment found for order {order_id}")
        await query.message.reply_text(
            "🔍 暂未检测到匹配的支付\n\n"
            "请确认：\n"
            "1. ✓ 已完成转账\n"
            "2. ✓ 转账金额正确（${:.4f} USDT）\n"
            "3. ✓ 使用了 TRC20 网络\n"
            "4. ✓ 转账地址正确\n\n"
            "💡 区块链确认通常需要 1-3 分钟\n"
            "如果您刚刚完成支付，请稍后再试。".format(amount_to_check)
        )
        
    except Exception as e:
        logger.error(f"Error verifying payment for order {order_id}: {e}", exc_info=True)
        await query.message.reply_text(
            "❌ 验证过程出现错误\n\n"
            "可能的原因：\n"
            "1. 网络连接问题\n"
            "2. 区块链 API 临时不可用\n\n"
            "请稍后重试，或联系管理员。"
        )

async def cancel_order(query, order_id: str):
    """Cancel an order"""
    db.update_order_status(order_id, 'cancelled')
    
    # Delete original message (payment info is sent as photo, can't use edit_message_text)
    try:
        await query.message.delete()
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")
    
    # Send new cancellation message
    await query.message.reply_text(
        "❌ 订单已取消\n\n使用 /start 返回主菜单",
        reply_markup=keyboards.get_back_to_main_keyboard()
    )
    utils.log_order_action(order_id, "Cancelled", "User cancelled")

# ============================================================================
# ADMIN FUNCTIONS
# ============================================================================

async def show_admin_panel(query, user):
    """Show admin panel"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    keyboard = keyboards.get_admin_panel_keyboard()
    await query.edit_message_text("👑 管理员面板", reply_markup=keyboard)

async def admin_check_balance(query, user):
    """Admin check Fragment balance"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    await query.edit_message_text("🔍 正在查询 Fragment 余额...")
    
    balance = await fragment.get_balance()
    
    if balance is not None:
        await query.edit_message_text(
            f"💰 Fragment 余额：{balance:.2f} TON",
            reply_markup=keyboards.get_admin_panel_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ 无法查询余额\n\n请检查 Fragment 登录状态",
            reply_markup=keyboards.get_admin_panel_keyboard()
        )

async def show_admin_stats(query, user):
    """Show admin statistics"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    # Gather statistics
    order_stats = db.get_order_statistics()
    income_stats = db.get_income_statistics()
    user_stats = db.get_user_count_statistics()
    
    stats = {
        'orders': order_stats,
        'income': income_stats,
        'users': user_stats
    }
    
    message = messages.get_admin_stats_message(stats)
    keyboard = keyboards.get_admin_panel_keyboard()
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def admin_login(query, user):
    """Admin login to Fragment via Telegram"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    # Check if phone number is configured
    if not config.TELEGRAM_PHONE or config.TELEGRAM_PHONE == '+8613800138000':
        await query.edit_message_text(
            "❌ <b>未配置 Telegram 手机号</b>\n\n"
            "<b>配置步骤：</b>\n"
            "1️⃣ 编辑 .env 文件\n"
            "2️⃣ 设置 TELEGRAM_PHONE=+你的手机号（国际格式）\n"
            "3️⃣ 示例：TELEGRAM_PHONE=+8613800138000\n"
            "4️⃣ 重启机器人\n\n"
            "<b>注意：</b>使用国际格式，包含国家代码",
            parse_mode='HTML'
        )
        return
    
    await query.edit_message_text(
        "🔐 开始 Telegram 登录流程...\n\n"
        "使用 Telethon + Fragment API 方式\n"
        "首次登录需要输入验证码\n"
        "⏳ 请等待..."
    )
    
    try:
        success = await fragment.login_with_telegram()
        
        if success:
            await query.message.reply_text(
                "✅ <b>Telegram 登录成功！</b>\n\n"
                "🎉 Fragment API 已就绪\n"
                "💎 可以自动开通 Premium 会员了",
                parse_mode='HTML'
            )
        else:
            await query.message.reply_text(
                "❌ <b>Telegram 登录失败</b>\n\n"
                "<b>可能的原因：</b>\n"
                "1️⃣ 手机号配置错误\n"
                "2️⃣ 未及时输入验证码\n"
                "3️⃣ 网络连接问题\n\n"
                "<b>解决方法：</b>\n"
                "• 检查 .env 中的 TELEGRAM_PHONE\n"
                "• 确保手机号格式正确\n"
                "• 查看日志获取详细信息\n\n"
                "<b>日志命令：</b>\n"
                "<code>journalctl -u telegram-premium-bot -n 50</code>",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Exception in admin_login: {e}", exc_info=True)
        await query.message.reply_text(
            f"❌ <b>登录过程中发生异常</b>\n\n"
            f"<b>错误类型：</b> {type(e).__name__}\n"
            f"<b>错误信息：</b> {str(e)[:200]}\n\n"
            f"<b>建议操作：</b>\n"
            f"• 检查 Telethon 是否正确安装\n"
            f"• 确认 .env 配置正确",
            parse_mode='HTML'
        )

async def show_order_details(query, order_id: str):
    """Show detailed order information"""
    order = db.get_order(order_id)
    
    if not order:
        await query.answer("❌ 订单不存在", show_alert=True)
        return
    
    # Check if user owns this order or is admin
    if order['user_id'] != query.from_user.id and not is_admin(query.from_user.id):
        await query.answer("❌ 您没有权限查看此订单", show_alert=True)
        return
    
    # Get user info for display
    user = db.get_user(order['user_id'])
    order['username'] = user.get('username') if user else None
    
    message = messages.get_order_details_message(order)
    keyboard = keyboards.get_back_to_main_keyboard()
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_admin_stats_orders(query, user):
    """Show admin order statistics"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    stats = db.get_order_statistics()
    
    message = f"""
📊 **订单统计详情**
━━━━━━━━━━━━━━

📦 总订单数：**{stats['total']}**
⏳ 待支付：{stats['pending']}
💰 已支付：{stats['paid']}
✅ 已完成：{stats['completed']}
❌ 失败/取消：{stats['failed']}

📈 成功率：**{stats['success_rate']:.1f}%**

━━━━━━━━━━━━━━
💡 提示：成功率 = 已完成 / 总订单数
"""
    
    keyboard = keyboards.get_admin_stats_keyboard()
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_admin_stats_income(query, user):
    """Show admin income statistics"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    stats = db.get_income_statistics()
    
    message = f"""
💰 **收入统计详情**
━━━━━━━━━━━━━━

📅 今日收入：**${stats['today']:.2f} USDT**
📅 本周收入：**${stats['week']:.2f} USDT**
📅 本月收入：**${stats['month']:.2f} USDT**

━━━━━━━━━━━━━━
💵 总收入：**${stats['total']:.2f} USDT**

━━━━━━━━━━━━━━
💡 提示：统计基于已完成的订单
"""
    
    keyboard = keyboards.get_admin_stats_keyboard()
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_admin_stats_users(query, user):
    """Show admin user statistics"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    stats = db.get_user_count_statistics()
    
    message = f"""
👥 **用户统计详情**
━━━━━━━━━━━━━━

👤 总用户数：**{stats['total']}**
🆕 今日新增：{stats['today']}
⭐ 活跃用户：{stats['active']}

━━━━━━━━━━━━━━
📊 活跃率：**{(stats['active']/stats['total']*100 if stats['total'] > 0 else 0):.1f}%**

━━━━━━━━━━━━━━
💡 提示：活跃用户 = 有已完成订单的用户
"""
    
    keyboard = keyboards.get_admin_stats_keyboard()
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_admin_prices(query, user):
    """Show admin price management"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    premium_prices = db.get_prices()
    stars_prices = db.get_stars_prices()
    
    message = f"""
💵 **价格管理**
━━━━━━━━━━━━━━

💎 **Premium 会员价格**
• 3个月：${premium_prices[3]:.2f} USDT
• 6个月：${premium_prices[6]:.2f} USDT
• 12个月：${premium_prices[12]:.2f} USDT

⭐ **Stars 价格**
• 100 Stars：${stars_prices[100]:.2f} USDT
• 250 Stars：${stars_prices[250]:.2f} USDT
• 500 Stars：${stars_prices[500]:.2f} USDT
• 1000 Stars：${stars_prices[1000]:.2f} USDT
• 2500 Stars：${stars_prices[2500]:.2f} USDT

━━━━━━━━━━━━━━
💡 使用命令修改价格：
/setprice <月数> <价格>
例如：/setprice 3 5.99
"""
    
    keyboard = keyboards.get_admin_panel_keyboard()
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_admin_orders(query, user):
    """Show admin order management"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    # Get recent orders
    all_orders = list(db.orders.find().sort('created_at', -1).limit(10))
    
    if not all_orders:
        message = "📋 暂无订单"
    else:
        message = "📋 **最近10个订单**\n━━━━━━━━━━━━━━\n\n"
        
        
        for order in all_orders:
            status_emoji = ORDER_STATUS_EMOJI.get(order.get('status', 'pending'), '❓')
            product_name = utils.get_product_name(
                order.get('product_type', PRODUCT_TYPE_PREMIUM),
                months=order.get('months'),
                stars=order.get('product_quantity')
            )
            
            user_info = db.get_user(order['user_id'])
            username = f"@{user_info.get('username')}" if user_info and user_info.get('username') else f"ID:{order['user_id']}"
            
            created_time = order['created_at'].strftime('%m-%d %H:%M')
            
            message += f"{status_emoji} **{product_name}**\n"
            message += f"   👤 {username} | 💰 ${order['price']:.2f}\n"
            message += f"   🆔 `{order['order_id'][:16]}...`\n"
            message += f"   🕐 {created_time}\n\n"
    
    keyboard = keyboards.get_admin_panel_keyboard()
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add startup callback to log bot identity
    async def post_init(app: Application) -> None:
        """Log bot identity on startup"""
        try:
            bot = await app.bot.get_me()
            logger.info("=" * 60)
            logger.info("🤖 Bot Identity:")
            logger.info(f"   Bot ID: {bot.id}")
            logger.info(f"   Bot Username: @{bot.username}")
            logger.info(f"   Bot Name: {bot.first_name}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Failed to get bot identity: {e}")
    
    application.post_init = post_init
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Admin command handlers
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("setprice", setprice_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("login", login_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler for text input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
