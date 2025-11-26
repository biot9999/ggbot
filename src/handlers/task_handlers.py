"""Telegram Advertising Bot - Task Handlers"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from ..config import config
from ..models import TaskStatus
from ..services import (
    AccountService,
    SendingService,
    TargetService,
    TaskService,
    TemplateService,
)
from ..utils import setup_logging
from .keyboards import (
    back_keyboard,
    confirm_keyboard,
    task_create_accounts_keyboard,
    task_create_targets_keyboard,
    task_create_templates_keyboard,
    task_detail_keyboard,
    tasks_menu_keyboard,
)

logger = setup_logging("task_handlers")


class TaskHandlers:
    """Handlers for task management."""

    def __init__(
        self,
        task_service: TaskService,
        account_service: AccountService,
        target_service: TargetService,
        template_service: TemplateService,
    ):
        self.task_service = task_service
        self.account_service = account_service
        self.target_service = target_service
        self.template_service = template_service
        self.pending_tasks: Dict[int, Dict] = {}  # user_id -> task creation data

    def register(self, app: Client):
        """Register handlers with the bot."""
        
        @app.on_callback_query(filters.regex(r"^menu_tasks$"))
        async def tasks_menu(client: Client, callback: CallbackQuery):
            await callback.answer()
            tasks = self.task_service.get_all_tasks()
            running = len([t for t in tasks if t.status == TaskStatus.RUNNING])
            pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
            
            await callback.message.edit_text(
                f"📤 **Task Management**\n\n"
                f"Total Tasks: {len(tasks)}\n"
                f"Running: {running}\n"
                f"Pending: {pending}\n\n"
                f"Create and manage sending tasks.",
                reply_markup=tasks_menu_keyboard(),
            )

        @app.on_callback_query(filters.regex(r"^task_create$"))
        async def task_create_start(client: Client, callback: CallbackQuery):
            await callback.answer()
            
            # Check prerequisites
            accounts = self.account_service.get_active_accounts()
            if not accounts:
                await callback.message.edit_text(
                    "❌ No active accounts available.\n\n"
                    "Please add and validate accounts first.",
                    reply_markup=back_keyboard("menu_tasks"),
                )
                return
            
            target_lists = self.target_service.get_all_lists()
            if not target_lists:
                await callback.message.edit_text(
                    "❌ No target lists available.\n\n"
                    "Please upload a target list first.",
                    reply_markup=back_keyboard("menu_tasks"),
                )
                return
            
            templates = self.template_service.get_all_templates()
            if not templates:
                await callback.message.edit_text(
                    "❌ No message templates available.\n\n"
                    "Please create a template first.",
                    reply_markup=back_keyboard("menu_tasks"),
                )
                return
            
            # Initialize task creation
            self.pending_tasks[callback.from_user.id] = {
                "step": "accounts",
                "selected_accounts": [],
            }
            
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 1/4: Select accounts to use.\n"
                "Choose one or more accounts:",
                reply_markup=task_create_accounts_keyboard(accounts, []),
            )

        @app.on_callback_query(filters.regex(r"^task_toggle_account:(.+)$"))
        async def task_toggle_account(client: Client, callback: CallbackQuery):
            await callback.answer()
            session_file = callback.matches[0].group(1)
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            data = self.pending_tasks[user_id]
            selected = data.get("selected_accounts", [])
            
            if session_file in selected:
                selected.remove(session_file)
            else:
                selected.append(session_file)
            
            data["selected_accounts"] = selected
            
            accounts = self.account_service.get_active_accounts()
            await callback.message.edit_text(
                f"➕ **Create Task**\n\n"
                f"Step 1/4: Select accounts to use.\n"
                f"Selected: {len(selected)} accounts",
                reply_markup=task_create_accounts_keyboard(accounts, selected),
            )

        @app.on_callback_query(filters.regex(r"^task_select_all_accounts$"))
        async def task_select_all_accounts(client: Client, callback: CallbackQuery):
            await callback.answer()
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            accounts = self.account_service.get_active_accounts()
            selected = [a.session_file for a in accounts]
            self.pending_tasks[user_id]["selected_accounts"] = selected
            
            await callback.message.edit_text(
                f"➕ **Create Task**\n\n"
                f"Step 1/4: Select accounts to use.\n"
                f"Selected: {len(selected)} accounts",
                reply_markup=task_create_accounts_keyboard(accounts, selected),
            )

        @app.on_callback_query(filters.regex(r"^task_clear_all_accounts$"))
        async def task_clear_all_accounts(client: Client, callback: CallbackQuery):
            await callback.answer()
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            self.pending_tasks[user_id]["selected_accounts"] = []
            
            accounts = self.account_service.get_active_accounts()
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 1/4: Select accounts to use.\n"
                "Selected: 0 accounts",
                reply_markup=task_create_accounts_keyboard(accounts, []),
            )

        @app.on_callback_query(filters.regex(r"^task_create_next$"))
        async def task_create_next(client: Client, callback: CallbackQuery):
            await callback.answer()
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            data = self.pending_tasks[user_id]
            
            if not data.get("selected_accounts"):
                await callback.answer("Please select at least one account", show_alert=True)
                return
            
            data["step"] = "targets"
            target_lists = self.target_service.get_all_lists()
            
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 2/4: Select target list:",
                reply_markup=task_create_targets_keyboard(target_lists),
            )

        @app.on_callback_query(filters.regex(r"^task_create_targets$"))
        async def task_create_targets(client: Client, callback: CallbackQuery):
            await callback.answer()
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            target_lists = self.target_service.get_all_lists()
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 2/4: Select target list:",
                reply_markup=task_create_targets_keyboard(target_lists),
            )

        @app.on_callback_query(filters.regex(r"^task_select_targets:(.+)$"))
        async def task_select_targets(client: Client, callback: CallbackQuery):
            await callback.answer()
            list_name = callback.matches[0].group(1)
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            self.pending_tasks[user_id]["target_list"] = list_name
            self.pending_tasks[user_id]["step"] = "template"
            
            templates = self.template_service.get_all_templates()
            
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 3/4: Select message template:",
                reply_markup=task_create_templates_keyboard(templates),
            )

        @app.on_callback_query(filters.regex(r"^task_select_template:(.+)$"))
        async def task_select_template(client: Client, callback: CallbackQuery):
            await callback.answer()
            template_id = callback.matches[0].group(1)
            user_id = callback.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            self.pending_tasks[user_id]["template_id"] = template_id
            self.pending_tasks[user_id]["step"] = "name"
            
            await callback.message.edit_text(
                "➕ **Create Task**\n\n"
                "Step 4/4: Send a name for this task:",
                reply_markup=back_keyboard("task_create_targets"),
            )

        @app.on_message(filters.text & filters.private)
        async def handle_task_name(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in self.pending_tasks:
                return
            
            data = self.pending_tasks[user_id]
            
            if data.get("step") != "name":
                return
            
            task_name = message.text.strip()
            
            # Create the task
            task = self.task_service.create_task(
                name=task_name,
                template_id=data["template_id"],
                target_list_file=data["target_list"],
                accounts=data["selected_accounts"],
            )
            
            del self.pending_tasks[user_id]
            
            await message.reply_text(
                f"✅ **Task Created!**\n\n"
                f"ID: {task.id}\n"
                f"Name: {task.name}\n"
                f"Accounts: {len(task.accounts)}\n"
                f"Target List: {task.target_list_file}\n\n"
                f"Use 'Start' to begin sending.",
                reply_markup=task_detail_keyboard(task.id, task.status.value),
            )

        @app.on_callback_query(filters.regex(r"^task_list$"))
        async def task_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            tasks = self.task_service.get_all_tasks()
            
            if not tasks:
                await callback.message.edit_text(
                    "📋 **Task List**\n\n"
                    "No tasks found. Create one to get started.",
                    reply_markup=tasks_menu_keyboard(),
                )
                return
            
            text = "📋 **Task List**\n\n"
            status_emoji = {
                "pending": "⏳",
                "running": "▶️",
                "paused": "⏸",
                "completed": "✅",
                "cancelled": "⏹",
                "failed": "❌",
            }
            
            for task in tasks:
                emoji = status_emoji.get(task.status.value, "❓")
                text += f"{emoji} **{task.name}** ({task.id})\n"
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for task in tasks:
                emoji = status_emoji.get(task.status.value, "❓")
                buttons.append([
                    InlineKeyboardButton(
                        f"{emoji} {task.name}",
                        callback_data=f"task_detail:{task.id}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_tasks")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^task_running$"))
        async def task_running_list(client: Client, callback: CallbackQuery):
            await callback.answer()
            tasks = self.task_service.get_running_tasks()
            
            if not tasks:
                await callback.message.edit_text(
                    "▶️ **Running Tasks**\n\n"
                    "No tasks are currently running.",
                    reply_markup=tasks_menu_keyboard(),
                )
                return
            
            text = "▶️ **Running Tasks**\n\n"
            for task in tasks:
                text += f"**{task.name}**\n{task.get_progress_text()}\n\n"
            
            from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            buttons = []
            for task in tasks:
                buttons.append([
                    InlineKeyboardButton(
                        f"▶️ {task.name}",
                        callback_data=f"task_detail:{task.id}",
                    )
                ])
            buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="task_running")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_tasks")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        @app.on_callback_query(filters.regex(r"^task_detail:(.+)$"))
        async def task_detail(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            task = self.task_service.get_task(task_id)
            
            if not task:
                await callback.message.edit_text(
                    "❌ Task not found.",
                    reply_markup=back_keyboard("task_list"),
                )
                return
            
            status_emoji = {
                "pending": "⏳",
                "running": "▶️",
                "paused": "⏸",
                "completed": "✅",
                "cancelled": "⏹",
                "failed": "❌",
            }
            
            text = (
                f"📤 **Task Details**\n\n"
                f"ID: {task.id}\n"
                f"Name: {task.name}\n"
                f"Status: {status_emoji.get(task.status.value, '❓')} {task.status.value}\n\n"
                f"Template: {task.template_id}\n"
                f"Target List: {task.target_list_file}\n"
                f"Accounts: {len(task.accounts)}\n\n"
                f"{task.get_progress_text()}\n\n"
                f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
            
            if task.started_at:
                text += f"Started: {task.started_at.strftime('%Y-%m-%d %H:%M')}\n"
            if task.completed_at:
                text += f"Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=task_detail_keyboard(task.id, task.status.value),
            )

        @app.on_callback_query(filters.regex(r"^task_start:(.+)$"))
        async def task_start(client: Client, callback: CallbackQuery):
            await callback.answer("Starting task...")
            task_id = callback.matches[0].group(1)
            
            task = await self.task_service.start_task(task_id)
            
            if task:
                await callback.message.edit_text(
                    f"▶️ **Task Started!**\n\n"
                    f"Task '{task.name}' is now running.",
                    reply_markup=task_detail_keyboard(task.id, task.status.value),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to start task.",
                    reply_markup=back_keyboard("task_list"),
                )

        @app.on_callback_query(filters.regex(r"^task_pause:(.+)$"))
        async def task_pause(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            if self.task_service.pause_task(task_id):
                task = self.task_service.get_task(task_id)
                await callback.message.edit_text(
                    f"⏸ **Task Paused**\n\n"
                    f"{task.get_progress_text() if task else ''}",
                    reply_markup=task_detail_keyboard(task_id, "paused"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to pause task.",
                    reply_markup=back_keyboard("task_list"),
                )

        @app.on_callback_query(filters.regex(r"^task_resume:(.+)$"))
        async def task_resume(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            if self.task_service.resume_task(task_id):
                await callback.message.edit_text(
                    "▶️ **Task Resumed**",
                    reply_markup=task_detail_keyboard(task_id, "running"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to resume task.",
                    reply_markup=back_keyboard("task_list"),
                )

        @app.on_callback_query(filters.regex(r"^task_cancel:(.+)$"))
        async def task_cancel_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                "⚠️ **Cancel Task?**\n\n"
                "Are you sure you want to cancel this task?",
                reply_markup=confirm_keyboard("task_cancel", task_id),
            )

        @app.on_callback_query(filters.regex(r"^confirm_task_cancel:(.+)$"))
        async def task_cancel_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            if self.task_service.cancel_task(task_id):
                task = self.task_service.get_task(task_id)
                await callback.message.edit_text(
                    f"⏹ **Task Cancelled**\n\n"
                    f"{task.get_progress_text() if task else ''}",
                    reply_markup=task_detail_keyboard(task_id, "cancelled"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to cancel task.",
                    reply_markup=back_keyboard("task_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_task_cancel:(.+)$"))
        async def task_cancel_abort(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            task_id = callback.matches[0].group(1)
            callback.matches[0] = type('Match', (), {'group': lambda self, n: task_id})()
            await task_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^task_delete:(.+)$"))
        async def task_delete_confirm(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            await callback.message.edit_text(
                "⚠️ **Delete Task?**\n\n"
                "Are you sure you want to delete this task?",
                reply_markup=confirm_keyboard("task_delete", task_id),
            )

        @app.on_callback_query(filters.regex(r"^confirm_task_delete:(.+)$"))
        async def task_delete_execute(client: Client, callback: CallbackQuery):
            await callback.answer()
            task_id = callback.matches[0].group(1)
            
            if self.task_service.delete_task(task_id):
                await callback.message.edit_text(
                    "✅ Task deleted.",
                    reply_markup=back_keyboard("task_list"),
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete task.",
                    reply_markup=back_keyboard("task_list"),
                )

        @app.on_callback_query(filters.regex(r"^cancel_task_delete:(.+)$"))
        async def task_delete_cancel(client: Client, callback: CallbackQuery):
            await callback.answer("Cancelled")
            task_id = callback.matches[0].group(1)
            callback.matches[0] = type('Match', (), {'group': lambda self, n: task_id})()
            await task_detail(client, callback)

        @app.on_callback_query(filters.regex(r"^task_report:(.+)$"))
        async def task_report(client: Client, callback: CallbackQuery):
            await callback.answer("Generating report...")
            task_id = callback.matches[0].group(1)
            
            report_path = self.task_service.export_report(task_id)
            
            if report_path:
                await callback.message.reply_document(
                    document=str(report_path),
                    caption=f"📊 Task Report: {task_id}",
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to generate report.",
                    reply_markup=back_keyboard(f"task_detail:{task_id}"),
                )
