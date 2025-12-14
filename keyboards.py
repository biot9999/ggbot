"""Keyboard layouts for the bot"""

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
