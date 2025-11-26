"""
Telegram Advertising Bot - Main Application

A feature-rich Telegram bot for managing bulk message sending campaigns.

Features:
- Multi-account management with session file support
- Target user list management with blacklist
- Message template support (text, media, forwarding)
- Proxy pool management (HTTP/SOCKS5)
- Task scheduling and control
- Real-time progress tracking
"""
import asyncio
import logging
import sys
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message

from src.config import config
from src.handlers import (
    AccountHandlers,
    ProxyHandlers,
    TargetHandlers,
    TaskHandlers,
    TemplateHandlers,
    main_menu_keyboard,
    settings_menu_keyboard,
    back_keyboard,
)
from src.services import (
    AccountService,
    ProxyService,
    SendingService,
    TargetService,
    TaskService,
    TemplateService,
)
from src.utils import setup_logging

# Setup logging
logger = setup_logging("main")


class TelegramAdBot:
    """Main Telegram Advertising Bot application."""

    def __init__(self):
        self.app: Client = None
        self.account_service = AccountService()
        self.proxy_service = ProxyService()
        self.target_service = TargetService()
        self.template_service = TemplateService()
        self.sending_service = SendingService(
            self.account_service,
            self.target_service,
            self.template_service,
        )
        self.task_service = TaskService(self.sending_service)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return user_id in config.bot.admin_ids

    def setup_bot(self):
        """Setup the bot application."""
        if not config.bot.bot_token:
            logger.error("BOT_TOKEN not configured!")
            sys.exit(1)

        if not config.bot.api_id or not config.bot.api_hash:
            logger.error("API_ID and API_HASH not configured!")
            sys.exit(1)

        self.app = Client(
            name="telegram_ad_bot",
            api_id=config.bot.api_id,
            api_hash=config.bot.api_hash,
            bot_token=config.bot.bot_token,
            workdir=str(Path.cwd()),
        )

        self._register_handlers()
        logger.info("Bot setup complete")

    def _register_handlers(self):
        """Register all message and callback handlers."""
        # Register debug handler first to catch all private messages
        # This handler has group=-1 to run before other handlers for debugging
        @self.app.on_message(filters.private, group=-1)
        async def debug_private_message(client: Client, message: Message):
            """Debug handler to log all incoming private messages."""
            user_id = message.from_user.id if message.from_user else "unknown"
            username = message.from_user.username if message.from_user else None
            chat_id = message.chat.id if message.chat else "unknown"
            text = message.text[:100] if message.text else "(no text)"
            
            username_str = f"@{username}" if username else "(none)"
            logger.debug(
                f"[DEBUG] Private message received: "
                f"from_user.id={user_id}, username={username_str}, "
                f"chat.id={chat_id}, text={text!r}"
            )
            # Continue to other handlers
            message.continue_propagation()

        # Register service handlers
        account_handlers = AccountHandlers(self.account_service)
        account_handlers.register(self.app)

        proxy_handlers = ProxyHandlers(self.proxy_service)
        proxy_handlers.register(self.app)

        target_handlers = TargetHandlers(self.target_service)
        target_handlers.register(self.app)

        template_handlers = TemplateHandlers(self.template_service)
        template_handlers.register(self.app)

        task_handlers = TaskHandlers(
            self.task_service,
            self.account_service,
            self.target_service,
            self.template_service,
        )
        task_handlers.register(self.app)

        # Register main commands
        @self.app.on_message(filters.command("start") & filters.private)
        async def start_command(client: Client, message: Message):
            user_id = message.from_user.id
            username = message.from_user.username or "(none)"
            admin_ids = config.bot.admin_ids
            
            logger.info(
                f"/start command received from user_id={user_id}, "
                f"username=@{username}, admin_ids={sorted(admin_ids)}"
            )
            
            if not self.is_admin(user_id):
                logger.warning(
                    f"Access denied for user_id={user_id}: "
                    f"not in admin_ids={sorted(admin_ids)}"
                )
                # Provide diagnostic information for easier configuration
                if not admin_ids:
                    await message.reply_text(
                        "⚠️ **Configuration Issue**\n\n"
                        "No admin IDs are configured. The bot cannot verify access.\n\n"
                        f"**Your User ID:** `{user_id}`\n\n"
                        "To fix this, add your user ID to the `.env` file:\n"
                        f"`ADMIN_IDS={user_id}`\n\n"
                        "Then restart the bot."
                    )
                else:
                    await message.reply_text(
                        "⛔ **Access Denied**\n\n"
                        "You are not authorized to use this bot.\n\n"
                        f"**Your User ID:** `{user_id}`\n"
                        f"**Configured Admin IDs:** `{sorted(admin_ids)}`\n\n"
                        "If you should have access, ensure your user ID is in "
                        "the `ADMIN_IDS` environment variable."
                    )
                return

            logger.info(f"Admin access granted for user_id={user_id}")
            await message.reply_text(
                "🤖 **Telegram Advertising Bot**\n\n"
                "Welcome! This bot helps you manage bulk message sending campaigns.\n\n"
                "**Features:**\n"
                "• Multi-account management\n"
                "• Target user lists\n"
                "• Message templates\n"
                "• Proxy support\n"
                "• Task scheduling\n\n"
                "Use the menu below to get started.",
                reply_markup=main_menu_keyboard(),
            )

        @self.app.on_message(filters.command("ping") & filters.private)
        async def ping_command(client: Client, message: Message):
            """Health check command to verify bot is responding."""
            user_id = message.from_user.id
            logger.debug(f"/ping received from user_id={user_id}")
            
            if not self.is_admin(user_id):
                # Still respond to non-admins for basic connectivity check
                await message.reply_text("pong")
                return
            
            # Admins get detailed status
            admin_ids = config.bot.admin_ids
            await message.reply_text(
                "🏓 **pong**\n\n"
                f"Bot is running and responding to messages.\n"
                f"Your user ID: `{user_id}`\n"
                f"Admin IDs configured: `{sorted(admin_ids)}`"
            )

        @self.app.on_message(filters.command("help") & filters.private)
        async def help_command(client: Client, message: Message):
            if not self.is_admin(message.from_user.id):
                return

            await message.reply_text(
                "📚 **Help Guide**\n\n"
                "**Commands:**\n"
                "/start - Show main menu\n"
                "/help - Show this help message\n"
                "/status - Show bot status\n"
                "/stats - Show statistics\n"
                "/ping - Health check (confirms bot is responding)\n\n"
                "**Workflow:**\n"
                "1. Upload session files (Accounts)\n"
                "2. Upload target user list (Targets)\n"
                "3. Create message template (Templates)\n"
                "4. Configure proxies if needed (Proxies)\n"
                "5. Create and start a task (Tasks)\n\n"
                "**Variables for templates:**\n"
                "• {username} - Target username\n"
                "• {user_id} - Target user ID\n"
                "• {first_name} - Target first name\n"
                "• {date} - Current date\n"
                "• {time} - Current time\n\n"
                "**Buttons in templates:**\n"
                "Use format: [Button Text](https://url.com)",
                reply_markup=back_keyboard("menu_main"),
            )

        @self.app.on_message(filters.command("status") & filters.private)
        async def status_command(client: Client, message: Message):
            if not self.is_admin(message.from_user.id):
                return

            accounts = self.account_service.get_all_accounts()
            active_accounts = self.account_service.get_active_accounts()
            proxies = self.proxy_service.get_all_proxies()
            working_proxies = [p for p in proxies if p.is_working]
            target_lists = self.target_service.get_all_lists()
            templates = self.template_service.get_all_templates()
            tasks = self.task_service.get_all_tasks()
            running_tasks = self.task_service.get_running_tasks()

            await message.reply_text(
                "📊 **Bot Status**\n\n"
                f"**Accounts:**\n"
                f"• Total: {len(accounts)}\n"
                f"• Active: {len(active_accounts)}\n\n"
                f"**Proxies:**\n"
                f"• Total: {len(proxies)}\n"
                f"• Working: {len(working_proxies)}\n\n"
                f"**Target Lists:** {len(target_lists)}\n"
                f"**Templates:** {len(templates)}\n\n"
                f"**Tasks:**\n"
                f"• Total: {len(tasks)}\n"
                f"• Running: {len(running_tasks)}",
                reply_markup=main_menu_keyboard(),
            )

        @self.app.on_message(filters.command("stats") & filters.private)
        async def stats_command(client: Client, message: Message):
            if not self.is_admin(message.from_user.id):
                return

            accounts = self.account_service.get_all_accounts()
            total_sent = sum(a.messages_sent for a in accounts)
            total_errors = sum(a.errors for a in accounts)

            tasks = self.task_service.get_all_tasks()
            total_success = sum(t.success_count for t in tasks)
            total_failed = sum(t.failed_count for t in tasks)
            total_skipped = sum(t.skipped_count for t in tasks)

            await message.reply_text(
                "📈 **Statistics**\n\n"
                f"**Messages:**\n"
                f"• Total Sent: {total_sent}\n"
                f"• Errors: {total_errors}\n\n"
                f"**Task Results:**\n"
                f"• Successful: {total_success}\n"
                f"• Failed: {total_failed}\n"
                f"• Skipped: {total_skipped}",
                reply_markup=main_menu_keyboard(),
            )

        # Main menu callback
        @self.app.on_callback_query(filters.regex(r"^menu_main$"))
        async def main_menu(client, callback):
            await callback.answer()
            await callback.message.edit_text(
                "🤖 **Main Menu**\n\n"
                "Select an option below:",
                reply_markup=main_menu_keyboard(),
            )

        # Settings menu
        @self.app.on_callback_query(filters.regex(r"^menu_settings$"))
        async def settings_menu(client, callback):
            await callback.answer()
            await callback.message.edit_text(
                "⚙️ **Settings**\n\n"
                f"**Rate Limits:**\n"
                f"• Message Delay: {config.rate_limit.message_delay_min}-{config.rate_limit.message_delay_max}s\n"
                f"• Account Switch: {config.rate_limit.account_switch_delay}s\n"
                f"• Max Concurrent: {config.rate_limit.max_concurrent_tasks}\n\n"
                f"Configure these in .env file.",
                reply_markup=settings_menu_keyboard(),
            )

        @self.app.on_callback_query(filters.regex(r"^settings_rate_limits$"))
        async def settings_rate_limits(client, callback):
            await callback.answer()
            await callback.message.edit_text(
                "⏱ **Rate Limits**\n\n"
                f"• MESSAGE_DELAY_MIN: {config.rate_limit.message_delay_min}s\n"
                f"• MESSAGE_DELAY_MAX: {config.rate_limit.message_delay_max}s\n"
                f"• ACCOUNT_SWITCH_DELAY: {config.rate_limit.account_switch_delay}s\n"
                f"• MAX_CONCURRENT_TASKS: {config.rate_limit.max_concurrent_tasks}\n\n"
                "Edit .env file to change these values.",
                reply_markup=back_keyboard("menu_settings"),
            )

        @self.app.on_callback_query(filters.regex(r"^settings_stats$"))
        async def settings_stats(client, callback):
            await callback.answer()
            await stats_command(client, callback.message)

        @self.app.on_callback_query(filters.regex(r"^settings_logs$"))
        async def settings_logs(client, callback):
            await callback.answer()
            
            # Get latest log file
            log_files = list(config.paths.log_dir.glob("*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                
                # Read last 50 lines
                with open(latest_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-50:]
                
                log_text = "".join(lines)
                if len(log_text) > 3500:
                    log_text = log_text[-3500:]
                
                await callback.message.edit_text(
                    f"📋 **Latest Logs**\n\n```\n{log_text}\n```",
                    reply_markup=back_keyboard("menu_settings"),
                )
            else:
                await callback.message.edit_text(
                    "📋 **Logs**\n\nNo log files found.",
                    reply_markup=back_keyboard("menu_settings"),
                )

    async def start(self):
        """Start the bot."""
        self.setup_bot()
        
        # Start task scheduler
        self.task_service.start_scheduler()
        
        logger.info("Starting bot...")
        await self.app.start()
        logger.info("Bot started successfully!")
        
        # Keep running
        await asyncio.Event().wait()

    async def stop(self):
        """Stop the bot."""
        logger.info("Stopping bot...")
        
        # Stop scheduler
        self.task_service.stop_scheduler()
        
        # Release all clients
        await self.account_service.release_all_clients()
        
        # Stop bot
        if self.app:
            await self.app.stop()
        
        logger.info("Bot stopped")


def main():
    """Main entry point."""
    bot = TelegramAdBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        asyncio.run(bot.stop())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
