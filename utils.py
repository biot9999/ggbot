"""Utility functions for the bot"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

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
        start = datetime(2020, 1, 1)  # Far past date
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
    from constants import ORDER_STATUS_EMOJI
    
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
