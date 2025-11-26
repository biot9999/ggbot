"""Telegram Advertising Bot - Target Handlers"""
from pathlib import Path
from typing import Dict

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from ..config import config
from ..services import TargetService
from ..utils import setup_logging
from .keyboards import (
    back_keyboard,
    blacklist_menu_keyboard,
    confirm_keyboard,
    target_list_detail_keyboard,
    targets_menu_keyboard,
)

logger = setup_logging("target_handlers")


class TargetHandlers:
    """Handlers for target user management."""

    def __init__(self, target_service: TargetService):
        self.target_service = target_service
        self.pending_uploads: Dict[int, bool] = {}
        self.pending_blacklist: Dict[int, bool] = {}

    def register(self, app: Client):
        """Register handlers with the bot."""
        
        @app.on_callback_query(filters.regex(r"^menu_targets$"))
        async def targets_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            await callback.message.edit_text(
                "👥 **Target User Management**\n\n"
                "Manage your target user lists here.\n"
                "Upload .txt files with usernames, user IDs, or phone numbers.",
                reply_markup=targets_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^target_upload$"))
        async def target_upload_prompt(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_uploads[callback.from_user.id] = True
            await callback.message.edit_text(
                "📤 **Upload Target List**\n\n"
                "Please send a .txt file with one target per line.\n\n"
                "Supported formats:\n"
                "• Usernames (with or without @)\n"
                "• User IDs (numeric)\n"
                "• Phone numbers (+1234567890)\n\n"
                "Lines starting with # are ignored.",
                reply_markup=back_keyboard("menu_targets"),
            )

        @app.on_message(filters.document & filters.private)
        async def handle_target_upload(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if we're waiting for a target file
            if not self.pending_uploads.get(user_id):
                return
            
            # Check if it's a text file
            if not message.document.file_name.endswith(".txt"):
                await message.reply_text(
                    "❌ Please send a .txt file.",
                    reply_markup=back_keyboard("menu_targets"),
                )
                return
            
            # Download the file
            file_path = await message.download(
                file_name=str(config.paths.target_dir / message.document.file_name)
            )
            
            self.pending_uploads[user_id] = False
            
            status_msg = await message.reply_text("⏳ Processing target list...")
            
            try:
                list_name, total_count, unique_count = self.target_service.import_from_file(
                    Path(file_path)
                )
                
                await status_msg.edit_text(
                    f"✅ **Target list imported!**\n\n"
                    f"📋 List Name: {list_name}\n"
                    f"📊 Total entries: {total_count}\n"
                    f"✅ Valid unique targets: {unique_count}\n"
                    f"🚫 Filtered (duplicates/blacklist): {total_count - unique_count}",
                    reply_markup=target_list_detail_keyboard(list_name),
                )
                
            except Exception as e:
                logger.error(f"Failed to import target list: {e}")
                await status_msg.edit_text(
                    f"❌ **Failed to import target list**\n\n"
                    f"Error: {str(e)}",
                    reply_markup=back_keyboard("menu_targets"),
                )

        @app.on_callback_query(filters.regex(r"^target_list$"))
        async def target_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            lists = self.target_service.get_all_lists()
            
            if not lists:
                await callback.message.edit_text(
                    "📋 **Target Lists**\n\n"
                    "No target lists found. Upload a .txt file to get started.",
                    reply_markup=targets_menu_keyboard(),
                )
                return
            
            text = "📋 **Target Lists**\n\n"
            for list_name, count in lists.items():
                text += f"📝 **{list_name}**: {count} targets\n"
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for list_name in lists.keys():
                buttons.append([
                    InlineKeyboardButton(
                        f"📋 {list_name}",
                        callback_data=f"target_detail:{list_name}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_targets")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^target_detail:(.+)$"))
        async def target_detail(client: Client, callback: CallbackQuery):
            await callback.answer()
            list_name = callback.matches[0].group(1)
            stats = self.target_service.get_stats(list_name)
            
            if not stats:
                await callback.message.edit_text(
                    "❌ Target list not found.",
                    reply_markup=back_keyboard("target_list"),
                )
                return
            
            text = (
                f"📋 **{list_name}**\n\n"
                f"📊 **Statistics:**\n"
                f"• Total: {stats['total']}\n"
                f"• Valid: {stats['valid']}\n"
                f"• Invalid: {stats['invalid']}\n\n"
                f"📈 **By Type:**\n"
                f"• Usernames: {stats['usernames']}\n"
                f"• User IDs: {stats['user_ids']}\n"
                f"• Phone Numbers: {stats['phones']}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=target_list_detail_keyboard(list_name),
            )

        @app.on_callback_query(filters.regex(r"^target_stats:(.+)$"))
        async def target_stats(client: Client, callback: CallbackQuery):
            # Same as target_detail
            await target_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^target_delete:(.+)$"))
        async def target_delete_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            list_name = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                f"⚠️ **Delete Target List?**\n\n"
                f"Are you sure you want to delete:\n"
                f"`{list_name}`\n\n"
                f"This action cannot be undone.",
                reply_markup=confirm_keyboard("target_delete", list_name),
            )

        @app.on_callback_query(filters.regex(r"^confirm_target_delete:(.+)$"))
        async def target_delete_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            list_name = callback.matches[0].group(1)
            
            if self.target_service.remove_target_list(list_name):
                await callback.message.edit_text(
                    "✅ Target list deleted successfully.",
                    reply_markup=back_keyboard("target_list"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete target list.",
                    reply_markup=back_keyboard("target_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_target_delete:(.+)$"))
        async def target_delete_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            list_name = callback.matches[0].group(1)
            # Create a mock callback with the correct pattern
            callback.matches[0] = type('Match', (), {'group': lambda self, n: list_name})()
            await target_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^target_blacklist$"))
        async def blacklist_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            blacklist = self.target_service.get_blacklist()
            
            await callback.message.edit_text(
                f"🚫 **Blacklist Management**\n\n"
                f"Current blacklist size: {len(blacklist)} entries\n\n"
                f"Blacklisted users will be skipped during message sending.",
                reply_markup=blacklist_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^blacklist_add$"))
        async def blacklist_add_prompt(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_blacklist[callback.from_user.id] = True
            await callback.message.edit_text(
                "➕ **Add to Blacklist**\n\n"
                "Send a username or user ID to add to the blacklist.\n"
                "You can send multiple entries, one per line.",
                reply_markup=back_keyboard("target_blacklist"),
            )

        @app.on_message(filters.text & filters.private)
        async def handle_blacklist_add(client: Client, message: Message):
            user_id = message.from_user.id
            
            # Check if we're waiting for blacklist entries
            if not self.pending_blacklist.get(user_id):
                return
            
            self.pending_blacklist[user_id] = False
            
            entries = message.text.strip().split("\n")
            added = 0
            
            for entry in entries:
                entry = entry.strip()
                if entry:
                    if self.target_service.add_to_blacklist(entry):
                        added += 1
            
            await message.reply_text(
                f"✅ Added {added} entries to blacklist.",
                reply_markup=back_keyboard("target_blacklist"),
            )

        @app.on_callback_query(filters.regex(r"^blacklist_view$"))
        async def blacklist_view(client: Client, callback: CallbackQuery):
            await callback.answer()
            blacklist = self.target_service.get_blacklist()
            
            if not blacklist:
                await callback.message.edit_text(
                    "📋 **Blacklist**\n\n"
                    "The blacklist is empty.",
                    reply_markup=back_keyboard("target_blacklist"),
                )
                return
            
            # Show first 50 entries
            entries = list(blacklist)[:50]
            text = "📋 **Blacklist**\n\n"
            text += "\n".join(f"• {entry}" for entry in entries)
            
            if len(blacklist) > 50:
                text += f"\n\n... and {len(blacklist) - 50} more entries"
            
            await callback.message.edit_text(
                text,
                reply_markup=back_keyboard("target_blacklist"),
            )

        @app.on_callback_query(filters.regex(r"^blacklist_clear$"))
        async def blacklist_clear_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            await callback.message.edit_text(
                "⚠️ **Clear Blacklist?**\n\n"
                "Are you sure you want to clear the entire blacklist?\n"
                "This action cannot be undone.",
                reply_markup=confirm_keyboard("blacklist_clear", "all"),
            )

        @app.on_callback_query(filters.regex(r"^confirm_blacklist_clear:all$"))
        async def blacklist_clear_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            count = self.target_service.clear_blacklist()
            await callback.message.edit_text(
                f"✅ Cleared {count} entries from blacklist.",
                reply_markup=back_keyboard("target_blacklist"),
            )

        @app.on_callback_query(filters.regex(r"^cancel_blacklist_clear:all$"))
        async def blacklist_clear_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            await blacklist_menu(client, callback)
