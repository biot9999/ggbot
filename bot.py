import logging
import asyncio
import qrcode
import io
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import config
from database import db
from payment import tron_payment
from fragment import fragment

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Active payment monitoring tasks
payment_tasks = {}

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.ADMIN_USER_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    db.create_user(user.id, user.username, user.first_name)
    
    welcome_message = f"""
🤖 欢迎使用 Telegram Premium 自动赠送机器人！

👋 你好 {user.first_name}！

💎 我可以帮你购买 Telegram Premium 会员
💰 支持 USDT (TRC20) 支付
⚡ 支付成功后自动开通

📱 可用命令：
/buy - 购买 Premium 会员
/status - 查看订单状态
/help - 获取帮助
"""
    
    if is_admin(user.id):
        welcome_message += """
👑 管理员命令：
/admin - 管理员面板
/setprice - 设置价格
/balance - 查看 Fragment 余额
/login - 登录 Fragment 账号
"""
    
    await update.message.reply_text(welcome_message)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command - show package options"""
    prices = db.get_prices()
    
    keyboard = [
        [InlineKeyboardButton(f"3个月 - ${prices[3]:.2f} USDT", callback_data="buy_3")],
        [InlineKeyboardButton(f"6个月 - ${prices[6]:.2f} USDT", callback_data="buy_6")],
        [InlineKeyboardButton(f"12个月 - ${prices[12]:.2f} USDT", callback_data="buy_12")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💎 请选择 Premium 套餐：\n\n"
        "📦 所有套餐均为正版 Telegram Premium\n"
        "⚡ 支付后自动开通，无需等待\n"
        "💰 支持 USDT (TRC20) 支付",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    if data.startswith("buy_"):
        # Extract months from callback data
        months = int(data.split("_")[1])
        await handle_purchase(query, user, months)
    
    elif data.startswith("paid_"):
        # User clicked "I have paid" button
        order_id = data.split("_", 1)[1]
        await verify_payment(query, order_id)
    
    elif data.startswith("cancel_"):
        # User cancelled order
        order_id = data.split("_", 1)[1]
        db.update_order_status(order_id, 'cancelled')
        await query.edit_message_text("❌ 订单已取消")

async def handle_purchase(query, user, months):
    """Handle purchase request"""
    # Get price
    prices = db.get_prices()
    price = prices[months]
    
    # Create order
    order_id = str(uuid.uuid4())
    db.create_order(order_id, user.id, months, price)
    
    # Generate QR code for payment
    payment_text = config.PAYMENT_WALLET_ADDRESS
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(payment_text)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    # Create payment buttons
    keyboard = [
        [InlineKeyboardButton("✅ 我已支付", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ 取消订单", callback_data=f"cancel_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"""
📦 订单详情
━━━━━━━━━━━━━━
🆔 订单号：`{order_id}`
⏰ 套餐：{months} 个月
💰 金额：{price:.2f} USDT

💳 付款信息
━━━━━━━━━━━━━━
🔹 网络：TRC20 (Tron)
🔹 代币：USDT
🔹 地址：`{config.PAYMENT_WALLET_ADDRESS}`

⚠️ 重要提示：
1. 请确保使用 TRC20 网络转账
2. 请转账准确金额：{price:.2f} USDT
3. 转账后点击"我已支付"按钮
4. 系统将自动验证并开通会员
5. 订单有效期：30分钟

🚫 防诈骗提示：
✓ 请确认转账到正确的地址
✓ 请使用真实 USDT，假币无法到账
✓ 系统会自动验证区块链交易
"""
    
    # Send QR code and payment info
    await query.message.reply_photo(
        photo=bio,
        caption=message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Start payment monitoring
    bot_instance = query.get_bot()
    asyncio.create_task(monitor_payment(bot_instance, order_id, user.id, price, query.message.chat_id))

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
                return
            
            # Record transaction
            db.create_transaction(
                tx_hash,
                order_id,
                payment_info['amount'],
                payment_info['from']
            )
            
            # Update order status
            db.update_order_status(order_id, 'paid', tx_hash)
            
            # Get order details
            order = db.get_order(order_id)
            
            # Send Premium
            success = await fragment.gift_premium(user_id, order['months'])
            
            if success:
                db.update_order_status(order_id, 'completed')
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ 支付成功！\n\n"
                         f"💎 {order['months']} 个月 Telegram Premium 已开通！\n"
                         f"📝 交易哈希：`{tx_hash}`\n\n"
                         f"感谢您的购买！",
                    parse_mode='Markdown'
                )
            else:
                db.update_order_status(order_id, 'failed')
                await bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ 支付已确认，但开通失败。\n"
                         "请联系管理员处理，订单号：`{order_id}`",
                    parse_mode='Markdown'
                )
        else:
            # Payment timeout
            order = db.get_order(order_id)
            if order['status'] == 'pending':
                db.update_order_status(order_id, 'expired')
                await bot.send_message(
                    chat_id=chat_id,
                    text="⏰ 订单已超时\n\n"
                         "未检测到付款，订单已自动取消。\n"
                         "如需购买，请重新下单。"
                )
    
    except Exception as e:
        logger.error(f"Error monitoring payment for order {order_id}: {e}")

async def verify_payment(query, order_id: str):
    """Manually verify payment when user clicks 'I have paid'"""
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ 订单不存在")
        return
    
    if order['status'] != 'pending':
        status_text = {
            'paid': '已支付，等待开通',
            'completed': '已完成',
            'failed': '失败',
            'expired': '已过期',
            'cancelled': '已取消'
        }.get(order['status'], order['status'])
        await query.edit_message_text(f"订单状态：{status_text}")
        return
    
    await query.edit_message_text(
        "🔍 正在验证支付...\n\n"
        "这可能需要几分钟，请稍候。\n"
        "我们会在验证完成后通知您。"
    )
    
    # Check for recent transactions
    try:
        transactions = await tron_payment.get_account_transactions(config.PAYMENT_WALLET_ADDRESS, 50)
        
        if transactions:
            for tx in transactions:
                # Check if amount matches
                tx_amount = float(tx.get('value', 0)) / (10 ** tx.get('token_info', {}).get('decimals', 6))
                
                if abs(tx_amount - order['price']) < 0.01:
                    tx_hash = tx.get('transaction_id')
                    
                    # Check if transaction already recorded
                    existing_tx = db.get_transaction(tx_hash)
                    if existing_tx:
                        continue
                    
                    # Verify authenticity
                    is_authentic = await tron_payment.verify_usdt_authenticity(tx_hash)
                    if not is_authentic:
                        await query.message.reply_text("❌ 检测到假 USDT！请使用真实的 USDT。")
                        db.update_order_status(order_id, 'failed')
                        return
                    
                    # Record transaction
                    db.create_transaction(tx_hash, order_id, tx_amount, tx.get('from'))
                    db.update_order_status(order_id, 'paid', tx_hash)
                    
                    # Gift Premium
                    success = await fragment.gift_premium(order['user_id'], order['months'])
                    
                    if success:
                        db.update_order_status(order_id, 'completed')
                        await query.message.reply_text(
                            f"✅ 支付验证成功！\n\n"
                            f"💎 {order['months']} 个月 Premium 已开通！\n"
                            f"感谢您的购买！"
                        )
                    else:
                        db.update_order_status(order_id, 'failed')
                        await query.message.reply_text(
                            "⚠️ 支付已确认，但开通失败。\n"
                            f"请联系管理员，订单号：{order_id}"
                        )
                    return
        
        await query.message.reply_text(
            "🔍 暂未检测到匹配的支付\n\n"
            "请确认：\n"
            "1. 已完成转账\n"
            "2. 转账金额正确\n"
            "3. 使用了 TRC20 网络\n\n"
            "区块链确认需要几分钟，请稍后再试。"
        )
        
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await query.message.reply_text("❌ 验证失败，请稍后重试")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show user's orders"""
    user_id = update.effective_user.id
    orders = db.get_user_orders(user_id)
    
    if not orders:
        await update.message.reply_text("📭 您还没有任何订单")
        return
    
    message = "📋 您的订单：\n\n"
    
    for order in orders[:5]:  # Show last 5 orders
        status_emoji = {
            'pending': '⏳',
            'paid': '💰',
            'completed': '✅',
            'failed': '❌',
            'expired': '⏰',
            'cancelled': '🚫'
        }.get(order['status'], '❓')
        
        status_text = {
            'pending': '待支付',
            'paid': '已支付',
            'completed': '已完成',
            'failed': '失败',
            'expired': '已过期',
            'cancelled': '已取消'
        }.get(order['status'], order['status'])
        
        message += f"{status_emoji} {order['months']}个月 - {status_text}\n"
        message += f"   订单号：`{order['order_id']}`\n"
        message += f"   金额：${order['price']:.2f} USDT\n"
        message += f"   时间：{order['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 使用帮助

💎 购买流程：
1. 发送 /buy 选择套餐
2. 扫描二维码或复制地址
3. 使用 USDT (TRC20) 支付
4. 点击"我已支付"按钮
5. 等待自动验证和开通

⚠️ 注意事项：
• 请使用 TRC20 网络
• 请转账准确金额
• 请使用真实 USDT
• 订单有效期 30 分钟

❓ 常见问题：
Q: 支付后多久到账？
A: 通常 1-5 分钟，最长不超过 30 分钟

Q: 支持哪些支付方式？
A: 目前仅支持 USDT (TRC20)

Q: 可以退款吗？
A: 数字商品不支持退款

需要帮助？请联系管理员
"""
    await update.message.reply_text(help_text)

# Admin commands
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    keyboard = [
        [InlineKeyboardButton("💰 查看余额", callback_data="admin_balance")],
        [InlineKeyboardButton("💵 设置价格", callback_data="admin_prices")],
        [InlineKeyboardButton("📊 订单统计", callback_data="admin_stats")],
        [InlineKeyboardButton("🔐 登录 Fragment", callback_data="admin_login")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("👑 管理员面板", reply_markup=reply_markup)

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
    
    await update.message.reply_text("🔍 正在查询 Fragment 余额...")
    
    balance = await fragment.get_balance()
    
    if balance is not None:
        await update.message.reply_text(f"💰 Fragment 余额：{balance:.2f} TON")
    else:
        await update.message.reply_text("❌ 无法查询余额，请检查 Fragment 登录状态")

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command - login to Fragment"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限使用此命令")
        return
    
    await update.message.reply_text(
        "🔐 开始 Fragment 登录流程...\n\n"
        "这需要在服务器上打开浏览器。\n"
        "登录过程会保存 session，之后无需重复登录。\n\n"
        "注意：此功能需要服务器支持图形界面或使用远程浏览器。"
    )
    
    success = await fragment.login_with_telegram()
    
    if success:
        await update.message.reply_text("✅ Fragment 登录成功！")
    else:
        await update.message.reply_text("❌ Fragment 登录失败")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Admin handlers
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("setprice", setprice_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("login", login_command))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
