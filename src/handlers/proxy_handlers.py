"""Telegram Advertising Bot - Proxy Handlers"""
from pathlib import Path
from typing import Dict

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from ..config import config
from ..models import ProxyType
from ..services import ProxyService
from ..utils import setup_logging
from .keyboards import (
    back_keyboard,
    confirm_keyboard,
    proxies_menu_keyboard,
    proxy_detail_keyboard,
)

logger = setup_logging("proxy_handlers")


class ProxyHandlers:
    """Handlers for proxy management."""

    def __init__(self, proxy_service: ProxyService):
        self.proxy_service = proxy_service
        self.pending_proxies: Dict[int, Dict] = {}
        self.pending_imports: Dict[int, bool] = {}

    def register(self, app: Client):
        """Register handlers with the bot."""
        
        @app.on_callback_query(filters.regex(r"^menu_proxies$"))
        async def proxies_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxies = self.proxy_service.get_all_proxies()
            working = sum(1 for p in proxies if p.is_working)
            
            await callback.message.edit_text(
                f"🌐 **Proxy Management**\n\n"
                f"Total Proxies: {len(proxies)}\n"
                f"Working: {working}\n\n"
                f"Configure proxies for your accounts.",
                reply_markup=proxies_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^proxy_add$"))
        async def proxy_add_prompt(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_proxies[callback.from_user.id] = {"step": "format"}
            await callback.message.edit_text(
                "➕ **Add Proxy**\n\n"
                "Send the proxy in one of these formats:\n\n"
                "• `socks5://host:port`\n"
                "• `socks5://user:pass@host:port`\n"
                "• `http://host:port`\n"
                "• `http://user:pass@host:port`\n"
                "• `host:port:user:pass` (assumes socks5)",
                reply_markup=back_keyboard("menu_proxies"),
            )

        @app.on_message(filters.text & filters.private)
        async def handle_proxy_input(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in self.pending_proxies:
                return
            
            data = self.pending_proxies[user_id]
            
            if data.get("step") == "format":
                del self.pending_proxies[user_id]
                
                proxy = self.proxy_service.parse_proxy_string(message.text)
                
                if proxy:
                    await message.reply_text(
                        f"✅ **Proxy added!**\n\n"
                        f"ID: {proxy.id}\n"
                        f"Type: {proxy.proxy_type.value}\n"
                        f"Host: {proxy.host}:{proxy.port}\n\n"
                        f"Testing proxy...",
                    )
                    
                    is_working = await self.proxy_service.test_proxy(proxy)
                    
                    await message.reply_text(
                        f"{'✅ Proxy is working!' if is_working else '❌ Proxy test failed.'}",
                        reply_markup=proxy_detail_keyboard(proxy.id),
                    )
                else:
                    await message.reply_text(
                        "❌ Invalid proxy format. Please try again.",
                        reply_markup=back_keyboard("menu_proxies"),
                    )

        @app.on_callback_query(filters.regex(r"^proxy_import$"))
        async def proxy_import_prompt(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_imports[callback.from_user.id] = True
            await callback.message.edit_text(
                "📤 **Import Proxies**\n\n"
                "Send a .txt file with one proxy per line.\n\n"
                "Supported formats:\n"
                "• `socks5://host:port`\n"
                "• `http://user:pass@host:port`\n"
                "• `host:port:user:pass`",
                reply_markup=back_keyboard("menu_proxies"),
            )

        @app.on_message(filters.document & filters.private)
        async def handle_proxy_file(client: Client, message: Message):
            user_id = message.from_user.id
            
            if not self.pending_imports.get(user_id):
                return
            
            if not message.document.file_name.endswith(".txt"):
                return
            
            self.pending_imports[user_id] = False
            
            file_path = await message.download(
                file_name=str(config.paths.proxy_file.parent / "import_temp.txt")
            )
            
            count = self.proxy_service.import_proxies_from_file(Path(file_path))
            
            # Clean up temp file
            Path(file_path).unlink(missing_ok=True)
            
            await message.reply_text(
                f"✅ Imported {count} proxies.\n\n"
                f"Use 'Test All Proxies' to verify them.",
                reply_markup=proxies_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^proxy_list$"))
        async def proxy_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxies = self.proxy_service.get_all_proxies()
            
            if not proxies:
                await callback.message.edit_text(
                    "📋 **Proxy List**\n\n"
                    "No proxies found. Add one to get started.",
                    reply_markup=proxies_menu_keyboard(),
                )
                return
            
            text = "📋 **Proxy List**\n\n"
            for proxy in proxies:
                status = "✅" if proxy.is_working else "❌"
                active = "🟢" if proxy.is_active else "🔴"
                text += f"{status}{active} {proxy.host}:{proxy.port} ({proxy.proxy_type.value})\n"
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for proxy in proxies:
                status = "✅" if proxy.is_working else "❌"
                buttons.append([
                    InlineKeyboardButton(
                        f"{status} {proxy.host}:{proxy.port}",
                        callback_data=f"proxy_detail:{proxy.id}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_proxies")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^proxy_detail:(.+)$"))
        async def proxy_detail(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            proxy = self.proxy_service.get_proxy(proxy_id)
            
            if not proxy:
                await callback.message.edit_text(
                    "❌ Proxy not found.",
                    reply_markup=back_keyboard("proxy_list"),
                )
                return
            
            status = "✅ Working" if proxy.is_working else "❌ Not Working"
            active = "🟢 Active" if proxy.is_active else "🔴 Disabled"
            
            text = (
                f"🌐 **Proxy Details**\n\n"
                f"ID: {proxy.id}\n"
                f"Type: {proxy.proxy_type.value}\n"
                f"Host: {proxy.host}\n"
                f"Port: {proxy.port}\n"
                f"Auth: {'Yes' if proxy.username else 'No'}\n\n"
                f"Status: {status}\n"
                f"State: {active}\n"
                f"Last Tested: {proxy.last_tested.strftime('%Y-%m-%d %H:%M') if proxy.last_tested else 'Never'}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=proxy_detail_keyboard(proxy_id),
            )

        @app.on_callback_query(filters.regex(r"^proxy_test:(.+)$"))
        async def proxy_test(client: Client, callback: CallbackQuery):
            await callback.answer("Testing...")
            proxy_id = callback.matches[0].group(1)
            proxy = self.proxy_service.get_proxy(proxy_id)
            
            if not proxy:
                await callback.message.edit_text(
                    "❌ Proxy not found.",
                    reply_markup=back_keyboard("proxy_list"),
                )
                return
            
            await callback.message.edit_text("⏳ Testing proxy...")
            
            is_working = await self.proxy_service.test_proxy(proxy)
            
            await callback.message.edit_text(
                f"{'✅ Proxy is working!' if is_working else '❌ Proxy test failed.'}",
                reply_markup=proxy_detail_keyboard(proxy_id),
            )

        @app.on_callback_query(filters.regex(r"^proxy_test_all$"))
        async def proxy_test_all(client: Client, callback: CallbackQuery):
            await callback.answer("Testing all proxies...")
            await callback.message.edit_text("⏳ Testing all proxies...")
            
            results = await self.proxy_service.test_all_proxies()
            
            working = sum(1 for v in results.values() if v)
            total = len(results)
            
            await callback.message.edit_text(
                f"✅ **Test Complete**\n\n"
                f"Working: {working}/{total} proxies",
                reply_markup=proxies_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^proxy_enable:(.+)$"))
        async def proxy_enable(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            
            self.proxy_service.update_proxy(proxy_id, is_active=True)
            
            await callback.message.edit_text(
                "✅ Proxy enabled.",
                reply_markup=proxy_detail_keyboard(proxy_id),
            )

        @app.on_callback_query(filters.regex(r"^proxy_disable:(.+)$"))
        async def proxy_disable(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            
            self.proxy_service.update_proxy(proxy_id, is_active=False)
            
            await callback.message.edit_text(
                "❌ Proxy disabled.",
                reply_markup=proxy_detail_keyboard(proxy_id),
            )

        @app.on_callback_query(filters.regex(r"^proxy_delete:(.+)$"))
        async def proxy_delete_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                "⚠️ **Delete Proxy?**\n\n"
                "Are you sure you want to delete this proxy?",
                reply_markup=confirm_keyboard("proxy_delete", proxy_id),
            )

        @app.on_callback_query(filters.regex(r"^confirm_proxy_delete:(.+)$"))
        async def proxy_delete_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            
            if self.proxy_service.remove_proxy(proxy_id):
                await callback.message.edit_text(
                    "✅ Proxy deleted.",
                    reply_markup=back_keyboard("proxy_list"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete proxy.",
                    reply_markup=back_keyboard("proxy_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_proxy_delete:(.+)$"))
        async def proxy_delete_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            proxy_id = callback.matches[0].group(1)
            callback.matches[0] = type('Match', (), {'group': lambda self, n: proxy_id})()
            await proxy_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^proxy_edit:(.+)$"))
        async def proxy_edit(client: Client, callback: CallbackQuery):
            await callback.answer()
            proxy_id = callback.matches[0].group(1)
            
            self.pending_proxies[callback.from_user.id] = {
                "step": "edit",
                "proxy_id": proxy_id,
            }
            
            await callback.message.edit_text(
                "✏️ **Edit Proxy**\n\n"
                "Send the new proxy configuration:\n\n"
                "• `socks5://host:port`\n"
                "• `http://user:pass@host:port`",
                reply_markup=back_keyboard(f"proxy_detail:{proxy_id}"),
            )
