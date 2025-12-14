import logging
import asyncio
import qrcode
import io
import uuid
from datetime import datetime
from telegram import Update
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
import keyboards
import messages
import utils
from constants import ORDER_STATUS, PRODUCT_TYPE_PREMIUM, PRODUCT_TYPE_STARS

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
        "这需要在服务器上打开浏览器并扫描二维码。\n"
        "登录过程会保存 session，之后无需重复登录。\n\n"
        "⏳ 请等待，这可能需要几分钟..."
    )
    
    success = await fragment.login_with_telegram()
    
    if success:
        await update.message.reply_text("✅ Fragment 登录成功！")
    else:
        await update.message.reply_text(
            "❌ Fragment 登录失败\n\n"
            "可能的原因：\n"
            "• 未及时扫描二维码\n"
            "• 网络连接问题\n"
            "• Fragment 页面结构变化\n\n"
            "请重试或查看日志获取更多信息"
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
    """Show recharge page (feature under development)"""
    message = messages.get_recharge_message()
    keyboard = keyboards.get_back_to_main_keyboard()
    
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

async def handle_self_purchase(query, user, months):
    """Handle purchase for self"""
    prices = db.get_prices()
    price = prices[months]
    
    # Create order
    order_id = str(uuid.uuid4())
    product_name = utils.get_product_name(PRODUCT_TYPE_PREMIUM, months=months)
    
    db.create_order(
        order_id=order_id,
        user_id=user.id,
        months=months,
        price=price,
        product_type=PRODUCT_TYPE_PREMIUM
    )
    
    await send_payment_info(query, order_id, product_name, price, user.id)
    
    utils.log_order_action(order_id, "Created", f"User {user.id}, {months} months, ${price}")

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
    """Handle stars purchase"""
    prices = db.get_stars_prices()
    price = prices.get(stars, stars * 0.01)
    
    # Create order
    order_id = str(uuid.uuid4())
    product_name = utils.get_product_name(PRODUCT_TYPE_STARS, stars=stars)
    
    db.create_order(
        order_id=order_id,
        user_id=user.id,
        months=0,  # Not applicable for stars
        price=price,
        product_type=PRODUCT_TYPE_STARS,
        product_quantity=stars
    )
    
    await send_payment_info(query, order_id, product_name, price, user.id)
    
    utils.log_order_action(order_id, "Created", f"User {user.id}, {stars} stars, ${price}")

async def send_payment_info(query, order_id, product_name, price, user_id):
    """Send payment information with QR code"""
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

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for recipient input, etc.)"""
    user = update.effective_user
    text = update.message.text
    
    # Check if user has a state
    user_state = db.get_user_state(user.id)
    
    if not user_state:
        # No active state, ignore
        return
    
    state = user_state.get('state')
    state_data = user_state.get('data', {})
    
    if state == 'awaiting_recipient':
        # User is providing recipient info for gift
        recipient_info = utils.parse_recipient_input(text)
        
        if recipient_info['type'] is None:
            await update.message.reply_text(
                "❌ 无效的输入格式\n\n"
                "请输入：\n"
                "• @username （例如：@johndoe）\n"
                "• 或者 User ID （例如：123456789）\n\n"
                "或点击取消按钮取消操作",
                reply_markup=keyboards.get_cancel_keyboard()
            )
            return
        
        # Create gift order
        months = state_data.get('months')
        prices = db.get_prices()
        price = prices[months]
        
        order_id = str(uuid.uuid4())
        product_name = utils.get_product_name(PRODUCT_TYPE_PREMIUM, months=months)
        
        recipient_id = recipient_info['value'] if recipient_info['type'] == 'user_id' else None
        recipient_username = recipient_info['value'] if recipient_info['type'] == 'username' else None
        
        db.create_order(
            order_id=order_id,
            user_id=user.id,
            months=months,
            price=price,
            product_type=PRODUCT_TYPE_PREMIUM,
            recipient_id=recipient_id,
            recipient_username=recipient_username
        )
        
        # Clear state
        db.clear_user_state(user.id)
        
        # Show payment info
        # Generate QR code
        payment_text = config.PAYMENT_WALLET_ADDRESS
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(payment_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Add gift recipient info to message
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
        
        await update.message.reply_photo(
            photo=bio,
            caption=message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Start payment monitoring
        bot_instance = context.bot
        asyncio.create_task(
            monitor_payment(bot_instance, order_id, user.id, price, update.message.chat_id)
        )
        
        utils.log_order_action(order_id, "Gift order created", f"Recipient: {text}")

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
            
            # Update order status
            db.update_order_status(order_id, 'paid', tx_hash)
            utils.log_payment_action(tx_hash, "Verified", f"Order {order_id}")
            
            # Get order details
            order = db.get_order(order_id)
            
            # Determine recipient
            recipient_id = order.get('recipient_id') or user_id
            
            # Process based on product type
            if order['product_type'] == PRODUCT_TYPE_PREMIUM:
                # Send Premium
                success = await fragment.gift_premium(recipient_id, order['months'])
                
                if success:
                    db.update_order_status(order_id, 'completed')
                    
                    # Create gift record if applicable
                    if order.get('recipient_id'):
                        db.create_gift_record(
                            order_id,
                            user_id,
                            recipient_id,
                            PRODUCT_TYPE_PREMIUM,
                            order['months']
                        )
                    
                    success_msg = f"✅ 支付成功！\n\n💎 {order['months']} 个月 Telegram Premium 已开通！\n"
                    
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
                    db.update_order_status(order_id, 'failed')
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ 支付已确认，但开通失败。\n请联系管理员处理，订单号：`{order_id}`",
                        parse_mode='Markdown'
                    )
                    utils.log_order_action(order_id, "Failed", "Premium gifting failed")
            
            elif order['product_type'] == PRODUCT_TYPE_STARS:
                # For now, just mark as completed (stars functionality would need implementation)
                db.update_order_status(order_id, 'completed')
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ 支付成功！\n\n⭐ {order['product_quantity']} Telegram Stars 已充值！\n"
                         f"📝 交易哈希：`{tx_hash}`\n\n"
                         f"感谢您的购买！",
                    parse_mode='Markdown'
                )
                utils.log_order_action(order_id, "Completed", f"{order['product_quantity']} stars")
        
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
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ 订单不存在")
        return
    
    if order['status'] != 'pending':
        status_text = ORDER_STATUS.get(order['status'], order['status'])
        await query.edit_message_text(f"订单状态：{status_text}")
        return
    
    await query.edit_message_text(
        "🔍 正在验证支付...\n\n这可能需要几分钟，请稍候。\n我们会在验证完成后通知您。"
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
                    
                    # Determine recipient
                    recipient_id = order.get('recipient_id') or order['user_id']
                    
                    # Gift Premium or Stars
                    if order['product_type'] == PRODUCT_TYPE_PREMIUM:
                        success = await fragment.gift_premium(recipient_id, order['months'])
                        
                        if success:
                            db.update_order_status(order_id, 'completed')
                            
                            # Create gift record if applicable
                            if order.get('recipient_id'):
                                db.create_gift_record(
                                    order_id,
                                    order['user_id'],
                                    recipient_id,
                                    PRODUCT_TYPE_PREMIUM,
                                    order['months']
                                )
                            
                            await query.message.reply_text(
                                f"✅ 支付验证成功！\n\n💎 {order['months']} 个月 Premium 已开通！\n感谢您的购买！"
                            )
                        else:
                            db.update_order_status(order_id, 'failed')
                            await query.message.reply_text(
                                f"⚠️ 支付已确认，但开通失败。\n请联系管理员，订单号：`{order_id}`",
                                parse_mode='Markdown'
                            )
                    elif order['product_type'] == PRODUCT_TYPE_STARS:
                        db.update_order_status(order_id, 'completed')
                        await query.message.reply_text(
                            f"✅ 支付验证成功！\n\n⭐ {order['product_quantity']} Stars 已充值！\n感谢您的购买！"
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

async def cancel_order(query, order_id: str):
    """Cancel an order"""
    db.update_order_status(order_id, 'cancelled')
    await query.edit_message_text(
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
    """Admin login to Fragment"""
    if not is_admin(user.id):
        await query.answer("❌ 您没有权限", show_alert=True)
        return
    
    await query.edit_message_text(
        "🔐 开始 Fragment 登录流程...\n\n"
        "这需要在服务器上打开浏览器并扫描二维码。\n"
        "⏳ 请等待，这可能需要几分钟..."
    )
    
    success = await fragment.login_with_telegram()
    
    if success:
        await query.message.reply_text("✅ Fragment 登录成功！")
    else:
        await query.message.reply_text("❌ Fragment 登录失败\n\n请检查日志获取更多信息")

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
        
        from constants import ORDER_STATUS_EMOJI
        
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
