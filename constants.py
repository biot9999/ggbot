"""Constants used throughout the bot"""

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
