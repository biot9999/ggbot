"""Telegram Advertising Bot - Account Handlers"""
from pathlib import Path
from typing import Dict

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from ..config import config
from ..services import AccountService
from ..utils import setup_logging
from .keyboards import (
    account_detail_keyboard,
    accounts_menu_keyboard,
    back_keyboard,
    confirm_keyboard,
)

logger = setup_logging("account_handlers")


class AccountHandlers:
    """Handlers for account management."""

    def __init__(self, account_service: AccountService):
        self.account_service = account_service
        self.pending_uploads: Dict[int, bool] = {}  # user_id -> waiting for session file

    def register(self, app: Client):
        """Register handlers with the bot."""
        
        @app.on_callback_query(filters.regex(r"^menu_accounts$"))
        async def accounts_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            await callback.message.edit_text(
                "📱 **Account Management**\n\n"
                "Manage your Telegram session accounts here.\n"
                "Upload .session files to add accounts.",
                reply_markup=accounts_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^account_upload$"))
        async def account_upload_prompt(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_uploads[callback.from_user.id] = True
            await callback.message.edit_text(
                "📤 **Upload Session File**\n\n"
                "Please send your .session file now.\n"
                "The file should be a valid Pyrogram or Telethon session file.",
                reply_markup=back_keyboard("menu_accounts"),
            )

        @app.on_message(filters.document & filters.private)
        async def handle_session_upload(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if we're waiting for a session file
            if not self.pending_uploads.get(user_id):
                return
            
            # Check if it's a session file
            if not message.document.file_name.endswith(".session"):
                await message.reply_text(
                    "❌ Please send a .session file.",
                    reply_markup=back_keyboard("menu_accounts"),
                )
                return
            
            # Download the file
            file_path = await message.download(
                file_name=str(config.paths.session_dir / message.document.file_name)
            )
            
            self.pending_uploads[user_id] = False
            
            status_msg = await message.reply_text("⏳ Validating session...")
            
            try:
                account = await self.account_service.import_session(Path(file_path))
                
                if account.status.value == "active":
                    await status_msg.edit_text(
                        f"✅ **Session imported successfully!**\n\n"
                        f"📱 User: @{account.username or 'N/A'}\n"
                        f"🆔 User ID: {account.user_id}\n"
                        f"📞 Phone: {account.phone or 'N/A'}\n"
                        f"✅ Status: Active",
                        reply_markup=account_detail_keyboard(account.session_file),
                    )
                else:
                    await status_msg.edit_text(
                        f"⚠️ **Session imported but validation failed**\n\n"
                        f"Status: {account.status.value}\n\n"
                        "The session file may be expired or invalid.",
                        reply_markup=account_detail_keyboard(account.session_file),
                    )
                    
            except Exception as e:
                logger.error(f"Failed to import session: {e}")
                await status_msg.edit_text(
                    f"❌ **Failed to import session**\n\n"
                    f"Error: {str(e)}",
                    reply_markup=back_keyboard("menu_accounts"),
                )

        @app.on_callback_query(filters.regex(r"^account_list$"))
        async def account_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            accounts = self.account_service.get_all_accounts()
            
            if not accounts:
                await callback.message.edit_text(
                    "📋 **Account List**\n\n"
                    "No accounts found. Upload a session file to get started.",
                    reply_markup=accounts_menu_keyboard(),
                )
                return
            
            text = "📋 **Account List**\n\n"
            for acc in accounts:
                status_emoji = {
                    "active": "✅",
                    "restricted": "⚠️",
                    "banned": "🚫",
                    "invalid": "❌",
                    "unknown": "❓",
                }.get(acc.status.value, "❓")
                
                text += (
                    f"{status_emoji} **{acc.username or acc.session_file}**\n"
                    f"   ID: {acc.user_id or 'N/A'} | Sent: {acc.messages_sent}\n\n"
                )
            
            # Create buttons for each account
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for acc in accounts:
                buttons.append([
                    InlineKeyboardButton(
                        f"{'✅' if acc.status.value == 'active' else '❌'} {acc.username or acc.session_file[:15]}",
                        callback_data=f"account_detail:{acc.session_file}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_accounts")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^account_detail:(.+)$"))
        async def account_detail(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            account = self.account_service.get_account(session_file)
            
            if not account:
                await callback.message.edit_text(
                    "❌ Account not found.",
                    reply_markup=back_keyboard("account_list"),
                )
                return
            
            status_emoji = {
                "active": "✅",
                "restricted": "⚠️",
                "banned": "🚫",
                "invalid": "❌",
                "unknown": "❓",
            }.get(account.status.value, "❓")
            
            text = (
                f"📱 **Account Details**\n\n"
                f"📁 Session: {account.session_file}\n"
                f"👤 Username: @{account.username or 'N/A'}\n"
                f"🆔 User ID: {account.user_id or 'N/A'}\n"
                f"📞 Phone: {account.phone or 'N/A'}\n"
                f"{status_emoji} Status: {account.status.value}\n"
                f"💬 Can Send: {'Yes' if account.can_send_messages else 'No'}\n"
                f"📤 Messages Sent: {account.messages_sent}\n"
                f"❌ Errors: {account.errors}\n"
                f"🌐 Proxy: {account.proxy_id or 'None'}\n"
                f"🕐 Last Used: {account.last_used.strftime('%Y-%m-%d %H:%M') if account.last_used else 'Never'}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=account_detail_keyboard(session_file),
            )

        @app.on_callback_query(filters.regex(r"^account_validate:(.+)$"))
        async def account_validate(client: Client, callback: CallbackQuery):
            await callback.answer("Validating...")
            session_file = callback.matches[0].group(1)
            account = self.account_service.get_account(session_file)
            
            if not account:
                await callback.message.edit_text(
                    "❌ Account not found.",
                    reply_markup=back_keyboard("account_list"),
                )
                return
            
            await callback.message.edit_text("⏳ Validating account...")
            
            account = await self.account_service.validate_account(account)
            
            status_emoji = "✅" if account.status.value == "active" else "❌"
            await callback.message.edit_text(
                f"{status_emoji} **Validation Result**\n\n"
                f"Status: {account.status.value}\n"
                f"Can Send Messages: {'Yes' if account.can_send_messages else 'No'}",
                reply_markup=account_detail_keyboard(session_file),
            )

        @app.on_callback_query(filters.regex(r"^account_validate_all$"))
        async def account_validate_all(client: Client, callback: CallbackQuery):
            await callback.answer("Validating all accounts...")
            await callback.message.edit_text("⏳ Validating all accounts...")
            
            await self.account_service.validate_all_accounts()
            accounts = self.account_service.get_all_accounts()
            
            active = sum(1 for a in accounts if a.status.value == "active")
            total = len(accounts)
            
            await callback.message.edit_text(
                f"✅ **Validation Complete**\n\n"
                f"Active: {active}/{total} accounts",
                reply_markup=accounts_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^account_delete:(.+)$"))
        async def account_delete_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                f"⚠️ **Delete Account?**\n\n"
                f"Are you sure you want to delete the session:\n"
                f"`{session_file}`\n\n"
                f"This action cannot be undone.",
                reply_markup=confirm_keyboard("account_delete", session_file),
            )

        @app.on_callback_query(filters.regex(r"^confirm_account_delete:(.+)$"))
        async def account_delete_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            
            if self.account_service.remove_account(session_file):
                await callback.message.edit_text(
                    "✅ Account deleted successfully.",
                    reply_markup=back_keyboard("account_list"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete account.",
                    reply_markup=back_keyboard("account_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_account_delete:(.+)$"))
        async def account_delete_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            session_file = callback.matches[0].group(1)
            # Go back to account detail
            await account_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^account_proxy:(.+)$"))
        async def account_proxy_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            
            from ..services import ProxyService
            proxy_service = ProxyService()
            proxies = proxy_service.get_all_proxies()
            
            if not proxies:
                await callback.message.edit_text(
                    "❌ No proxies available.\n\n"
                    "Please add proxies first.",
                    reply_markup=back_keyboard(f"account_detail:{session_file}"),
                )
                return
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            buttons.append([
                InlineKeyboardButton("🚫 No Proxy", callback_data=f"account_set_proxy:{session_file}:none")
            ])
            for proxy in proxies:
                status = "✅" if proxy.is_working else "❌"
                buttons.append([
                    InlineKeyboardButton(
                        f"{status} {proxy.host}:{proxy.port}",
                        callback_data=f"account_set_proxy:{session_file}:{proxy.id}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"account_detail:{session_file}")])
            
            await callback.message.edit_text(
                "🌐 **Select Proxy**\n\n"
                "Choose a proxy for this account:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^account_set_proxy:(.+):(.+)$"))
        async def account_set_proxy(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            proxy_id = callback.matches[0].group(2)
            
            if proxy_id == "none":
                proxy_id = None
            
            self.account_service.set_account_proxy(session_file, proxy_id)
            
            await callback.message.edit_text(
                f"✅ Proxy {'removed' if proxy_id is None else 'set'} successfully.",
                reply_markup=back_keyboard(f"account_detail:{session_file}"),
            )
