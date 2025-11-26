"""Telegram Advertising Bot - Template Handlers"""
import re
from pathlib import Path
from typing import Dict, Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from ..config import config
from ..services import TemplateService
from ..utils import setup_logging
from .keyboards import (
    back_keyboard,
    confirm_keyboard,
    template_detail_keyboard,
    templates_menu_keyboard,
)

logger = setup_logging("template_handlers")


class TemplateHandlers:
    """Handlers for message template management."""

    def __init__(self, template_service: TemplateService):
        self.template_service = template_service
        self.pending_templates: Dict[int, Dict] = {}  # user_id -> template data

    def register(self, app: Client):
        """Register handlers with the bot."""
        
        @app.on_callback_query(filters.regex(r"^menu_templates$"))
        async def templates_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            await callback.message.edit_text(
                "📝 **Message Templates**\n\n"
                "Create and manage message templates.\n"
                "Templates support variables like {username}, {user_id}.",
                reply_markup=templates_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^template_create_text$"))
        async def template_create_text(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_templates[callback.from_user.id] = {
                "type": "text",
                "step": "name",
            }
            await callback.message.edit_text(
                "📝 **Create Text Template**\n\n"
                "Step 1/2: Send a name for this template.",
                reply_markup=back_keyboard("menu_templates"),
            )

        @app.on_callback_query(filters.regex(r"^template_create_media$"))
        async def template_create_media(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_templates[callback.from_user.id] = {
                "type": "media",
                "step": "name",
            }
            await callback.message.edit_text(
                "📷 **Create Media Template**\n\n"
                "Step 1/3: Send a name for this template.",
                reply_markup=back_keyboard("menu_templates"),
            )

        @app.on_callback_query(filters.regex(r"^template_create_forward$"))
        async def template_create_forward(client: Client, callback: CallbackQuery):
            await callback.answer()
            self.pending_templates[callback.from_user.id] = {
                "type": "forward",
                "step": "name",
            }
            await callback.message.edit_text(
                "📢 **Create Forward Template**\n\n"
                "Step 1/3: Send a name for this template.",
                reply_markup=back_keyboard("menu_templates"),
            )

        @app.on_message(filters.text & filters.private)
        async def handle_template_text_input(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in self.pending_templates:
                return
            
            data = self.pending_templates[user_id]
            
            if data["step"] == "name":
                data["name"] = message.text
                
                if data["type"] == "text":
                    data["step"] = "text"
                    await message.reply_text(
                        "Step 2/2: Send the message text.\n\n"
                        "**Available variables:**\n"
                        "• {username} - Target username\n"
                        "• {user_id} - Target user ID\n"
                        "• {first_name} - Target first name\n"
                        "• {date} - Current date\n"
                        "• {time} - Current time",
                        reply_markup=back_keyboard("menu_templates"),
                    )
                elif data["type"] == "forward":
                    data["step"] = "channel"
                    await message.reply_text(
                        "Step 2/3: Send the channel username (with or without @).",
                        reply_markup=back_keyboard("menu_templates"),
                    )
                else:  # media
                    data["step"] = "media"
                    await message.reply_text(
                        "Step 2/3: Send the media file (photo, document, or video).",
                        reply_markup=back_keyboard("menu_templates"),
                    )
                    
            elif data["step"] == "text":
                # Text template - final step
                text = message.text
                
                # Check for buttons in format [text](url)
                button_pattern = r"\[(.+?)\]\((.+?)\)"
                buttons = []
                for match in re.finditer(button_pattern, text):
                    buttons.append({
                        "text": match.group(1),
                        "url": match.group(2),
                    })
                
                # Remove button syntax from text
                clean_text = re.sub(button_pattern, "", text).strip()
                
                template = self.template_service.create_text_template(
                    name=data["name"],
                    text=clean_text,
                    buttons=buttons if buttons else None,
                )
                
                del self.pending_templates[user_id]
                
                await message.reply_text(
                    f"✅ **Template created!**\n\n"
                    f"ID: {template.id}\n"
                    f"Name: {template.name}\n"
                    f"Buttons: {len(buttons)}",
                    reply_markup=template_detail_keyboard(template.id),
                )
                
            elif data["step"] == "channel":
                data["channel"] = message.text.strip().lstrip("@")
                data["step"] = "message_id"
                await message.reply_text(
                    "Step 3/3: Send the message ID to forward.\n\n"
                    "Tip: Forward the message to @userinfobot to get the message ID.",
                    reply_markup=back_keyboard("menu_templates"),
                )
                
            elif data["step"] == "message_id":
                try:
                    message_id = int(message.text)
                    
                    template = self.template_service.create_forward_template(
                        name=data["name"],
                        channel_username=data["channel"],
                        message_id=message_id,
                    )
                    
                    del self.pending_templates[user_id]
                    
                    await message.reply_text(
                        f"✅ **Forward template created!**\n\n"
                        f"ID: {template.id}\n"
                        f"Name: {template.name}\n"
                        f"Channel: @{template.forward_from_channel}\n"
                        f"Message ID: {template.forward_message_id}",
                        reply_markup=template_detail_keyboard(template.id),
                    )
                except ValueError:
                    await message.reply_text(
                        "❌ Invalid message ID. Please send a number.",
                        reply_markup=back_keyboard("menu_templates"),
                    )
                    
            elif data["step"] == "caption":
                # Media template - caption step
                caption = message.text
                
                # Check for buttons
                button_pattern = r"\[(.+?)\]\((.+?)\)"
                buttons = []
                for match in re.finditer(button_pattern, caption):
                    buttons.append({
                        "text": match.group(1),
                        "url": match.group(2),
                    })
                
                clean_caption = re.sub(button_pattern, "", caption).strip()
                
                template = self.template_service.create_media_template(
                    name=data["name"],
                    media_path=Path(data["media_path"]),
                    media_type=data["media_type"],
                    caption=clean_caption if clean_caption else None,
                    buttons=buttons if buttons else None,
                )
                
                del self.pending_templates[user_id]
                
                await message.reply_text(
                    f"✅ **Media template created!**\n\n"
                    f"ID: {template.id}\n"
                    f"Name: {template.name}\n"
                    f"Media Type: {template.media_type}",
                    reply_markup=template_detail_keyboard(template.id),
                )

        @app.on_message(filters.media & filters.private)
        async def handle_template_media_input(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in self.pending_templates:
                return
            
            data = self.pending_templates[user_id]
            
            if data.get("step") != "media":
                return
            
            # Determine media type
            if message.photo:
                media_type = "photo"
            elif message.document:
                media_type = "document"
            elif message.video:
                media_type = "video"
            else:
                await message.reply_text(
                    "❌ Unsupported media type. Please send a photo, document, or video.",
                    reply_markup=back_keyboard("menu_templates"),
                )
                return
            
            # Download media
            templates_dir = config.paths.target_dir.parent / "templates" / "media"
            templates_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = await message.download(file_name=str(templates_dir / f"temp_{user_id}"))
            
            data["media_path"] = file_path
            data["media_type"] = media_type
            data["step"] = "caption"
            
            await message.reply_text(
                "Step 3/3: Send a caption for the media (or send 'skip' for no caption).\n\n"
                "**Available variables:**\n"
                "• {username} - Target username\n"
                "• {user_id} - Target user ID\n\n"
                "**Add buttons with format:**\n"
                "[Button Text](https://url.com)",
                reply_markup=back_keyboard("menu_templates"),
            )

        @app.on_callback_query(filters.regex(r"^template_list$"))
        async def template_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            templates = self.template_service.get_all_templates()
            
            if not templates:
                await callback.message.edit_text(
                    "📋 **Templates**\n\n"
                    "No templates found. Create one to get started.",
                    reply_markup=templates_menu_keyboard(),
                )
                return
            
            text = "📋 **Templates**\n\n"
            for template in templates:
                type_emoji = "📝" if template.text else "📷" if template.media_path else "📢"
                text += f"{type_emoji} **{template.name}** (ID: {template.id})\n"
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for template in templates:
                buttons.append([
                    InlineKeyboardButton(
                        f"📝 {template.name}",
                        callback_data=f"template_detail:{template.id}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_templates")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^template_detail:(.+)$"))
        async def template_detail(client: Client, callback: CallbackQuery):
            await callback.answer()
            template_id = callback.matches[0].group(1)
            template = self.template_service.get_template(template_id)
            
            if not template:
                await callback.message.edit_text(
                    "❌ Template not found.",
                    reply_markup=back_keyboard("template_list"),
                )
                return
            
            preview = self.template_service.get_template_preview(template_id)
            
            await callback.message.edit_text(
                preview,
                reply_markup=template_detail_keyboard(template_id),
            )

        @app.on_callback_query(filters.regex(r"^template_preview:(.+)$"))
        async def template_preview(client: Client, callback: CallbackQuery):
            # Same as detail for now
            await template_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^template_edit:(.+)$"))
        async def template_edit(client: Client, callback: CallbackQuery):
            await callback.answer()
            template_id = callback.matches[0].group(1)
            
            self.pending_templates[callback.from_user.id] = {
                "type": "edit",
                "template_id": template_id,
                "step": "text",
            }
            
            await callback.message.edit_text(
                "✏️ **Edit Template**\n\n"
                "Send the new message text.\n\n"
                "**Available variables:**\n"
                "• {username} - Target username\n"
                "• {user_id} - Target user ID\n"
                "• {first_name} - Target first name\n"
                "• {date} - Current date\n"
                "• {time} - Current time",
                reply_markup=back_keyboard(f"template_detail:{template_id}"),
            )

        @app.on_callback_query(filters.regex(r"^template_delete:(.+)$"))
        async def template_delete_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            template_id = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                f"⚠️ **Delete Template?**\n\n"
                f"Are you sure you want to delete this template?\n"
                f"This action cannot be undone.",
                reply_markup=confirm_keyboard("template_delete", template_id),
            )

        @app.on_callback_query(filters.regex(r"^confirm_template_delete:(.+)$"))
        async def template_delete_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            template_id = callback.matches[0].group(1)
            
            if self.template_service.delete_template(template_id):
                await callback.message.edit_text(
                    "✅ Template deleted successfully.",
                    reply_markup=back_keyboard("template_list"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete template.",
                    reply_markup=back_keyboard("template_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_template_delete:(.+)$"))
        async def template_delete_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            template_id = callback.matches[0].group(1)
            callback.matches[0] = type('Match', (), {'group': lambda self, n: template_id})()
            await template_detail(client, callback)
