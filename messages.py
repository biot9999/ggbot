"""Message templates for the bot"""

from datetime import datetime
from constants import ORDER_STATUS, ORDER_STATUS_EMOJI

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
/balance - 查看余额
/login - 登录 Fragment
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
💰 订单金额：${price:.2f} USDT
💵 实付金额：${price:.2f} USDT

━━━━━━━━━━━━━━
💳 **付款信息**

🔹 网络：TRC20 (Tron)
🔹 代币：USDT
🔹 地址：
`{wallet_address}`

━━━━━━━━━━━━━━
⚠️ **重要提示**

1️⃣ 请确保使用 **TRC20 网络** 转账
2️⃣ 请转账准确金额：**${price:.2f} USDT**
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
    
    if recipient_info.get('photo_url'):
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
