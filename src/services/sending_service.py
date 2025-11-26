"""Telegram Advertising Bot - Message Sending Service"""
import asyncio
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserBlocked,
    UserIsBlocked,
    UserNotMutualContact,
    UserPrivacyRestricted,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import config
from ..models import Account, MessageTemplate, SendTask, TargetUser, TaskStatus
from ..utils import render_template, setup_logging
from .account_service import AccountService
from .target_service import TargetService
from .template_service import TemplateService

logger = setup_logging("sending_service")


class SendingService:
    """Service for sending messages."""

    def __init__(
        self,
        account_service: AccountService,
        target_service: TargetService,
        template_service: TemplateService,
    ):
        self.account_service = account_service
        self.target_service = target_service
        self.template_service = template_service
        self.active_tasks: Dict[str, SendTask] = {}
        self._task_locks: Dict[str, asyncio.Lock] = {}
        self._pause_events: Dict[str, asyncio.Event] = {}

    def _get_delay(self) -> float:
        """Get random delay between messages."""
        return random.uniform(
            config.rate_limit.message_delay_min,
            config.rate_limit.message_delay_max,
        )

    async def _resolve_target(
        self,
        client: Client,
        target: TargetUser,
    ) -> Optional[int]:
        """Resolve target to user ID."""
        try:
            if target.identifier_type == "user_id":
                return int(target.identifier)
            elif target.identifier_type == "username":
                user = await client.get_users(target.identifier)
                return user.id
            elif target.identifier_type == "phone":
                # Phone resolution requires contact import
                # This is more complex and may not work for all cases
                contacts = await client.get_contacts()
                for contact in contacts:
                    if contact.phone_number == target.identifier:
                        return contact.id
                return None
        except Exception as e:
            logger.debug(f"Failed to resolve target {target.identifier}: {e}")
            return None

    def _build_keyboard(
        self,
        buttons: Optional[List[Dict[str, str]]],
    ) -> Optional[InlineKeyboardMarkup]:
        """Build inline keyboard from button definitions."""
        if not buttons:
            return None
        
        keyboard = []
        for btn in buttons:
            keyboard.append([
                InlineKeyboardButton(
                    text=btn.get("text", "Link"),
                    url=btn.get("url", ""),
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)

    async def _send_message(
        self,
        client: Client,
        target_id: int,
        template: MessageTemplate,
        variables: Dict[str, str],
    ) -> bool:
        """Send a message to a target."""
        try:
            keyboard = self._build_keyboard(template.buttons)
            
            # Handle forwarding
            if template.forward_from_channel and template.forward_message_id:
                await client.forward_messages(
                    chat_id=target_id,
                    from_chat_id=template.forward_from_channel,
                    message_ids=template.forward_message_id,
                )
                return True
            
            # Render text with variables
            text = None
            if template.text:
                text = render_template(template.text, variables)
            
            # Send based on media type
            if template.media_path:
                media_type = template.media_type
                if media_type == "photo":
                    await client.send_photo(
                        chat_id=target_id,
                        photo=template.media_path,
                        caption=text,
                        reply_markup=keyboard,
                    )
                elif media_type == "document":
                    await client.send_document(
                        chat_id=target_id,
                        document=template.media_path,
                        caption=text,
                        reply_markup=keyboard,
                    )
                elif media_type == "video":
                    await client.send_video(
                        chat_id=target_id,
                        video=template.media_path,
                        caption=text,
                        reply_markup=keyboard,
                    )
            else:
                # Text only
                if text:
                    await client.send_message(
                        chat_id=target_id,
                        text=text,
                        reply_markup=keyboard,
                    )
            
            return True
            
        except FloodWait as e:
            logger.warning(f"FloodWait: waiting {e.value} seconds")
            await asyncio.sleep(e.value)
            return await self._send_message(client, target_id, template, variables)
            
        except (UserIsBlocked, UserBlocked):
            logger.debug(f"User {target_id} has blocked the account")
            return False
            
        except UserPrivacyRestricted:
            logger.debug(f"User {target_id} has privacy restrictions")
            return False
            
        except UserNotMutualContact:
            logger.debug(f"User {target_id} requires mutual contact")
            return False
            
        except PeerIdInvalid:
            logger.debug(f"Invalid peer ID: {target_id}")
            return False
            
        except InputUserDeactivated:
            logger.debug(f"User {target_id} is deactivated")
            return False
            
        except Exception as e:
            logger.error(f"Error sending to {target_id}: {e}")
            return False

    async def execute_task(self, task: SendTask) -> SendTask:
        """Execute a sending task."""
        task_id = task.id
        self._task_locks[task_id] = asyncio.Lock()
        self._pause_events[task_id] = asyncio.Event()
        self._pause_events[task_id].set()  # Not paused initially
        
        self.active_tasks[task_id] = task
        
        # Get template
        template = self.template_service.get_template(task.template_id)
        if not template:
            task.status = TaskStatus.FAILED
            logger.error(f"Template not found for task {task_id}")
            return task
        
        # Get targets
        targets = self.target_service.get_valid_targets(task.target_list_file)
        if not targets:
            task.status = TaskStatus.FAILED
            logger.error(f"No valid targets for task {task_id}")
            return task
        
        task.total_targets = len(targets)
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # Get active accounts
        accounts = [
            self.account_service.get_account(session)
            for session in task.accounts
        ]
        accounts = [a for a in accounts if a and a.can_send_messages]
        
        if not accounts:
            task.status = TaskStatus.FAILED
            logger.error(f"No active accounts for task {task_id}")
            return task
        
        logger.info(f"Starting task {task_id}: {len(targets)} targets, {len(accounts)} accounts")
        
        try:
            current_account_idx = task.current_account_index
            messages_per_account = 0
            max_messages_per_account = config.rate_limit.messages_per_account
            
            for i in range(task.current_target_index, len(targets)):
                # Check if cancelled
                if task.status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} cancelled")
                    break
                
                # Wait if paused
                await self._pause_events[task_id].wait()
                
                target = targets[i]
                task.current_target_index = i
                
                # Get current account and client
                account = accounts[current_account_idx]
                client = await self.account_service.get_client(account)
                
                if not client:
                    # Try next account
                    current_account_idx = (current_account_idx + 1) % len(accounts)
                    task.current_account_index = current_account_idx
                    messages_per_account = 0
                    continue
                
                # Resolve target
                target_id = await self._resolve_target(client, target)
                
                if not target_id:
                    task.skipped_count += 1
                    self.target_service.update_target_status(
                        task.target_list_file,
                        target.identifier,
                        is_valid=False,
                        error_message="Could not resolve user",
                    )
                    continue
                
                # Check blacklist
                if self.target_service.is_blacklisted(target.identifier):
                    task.skipped_count += 1
                    continue
                
                # Build variables for template
                variables = {
                    "username": target.username or target.identifier,
                    "user_id": str(target_id),
                }
                
                # Send message
                success = await self._send_message(client, target_id, template, variables)
                
                task.sent_count += 1
                if success:
                    task.success_count += 1
                    logger.debug(f"Sent to {target.identifier}")
                else:
                    task.failed_count += 1
                    task.error_log.append({
                        "target": target.identifier,
                        "error": "Send failed",
                        "timestamp": datetime.now().isoformat(),
                    })
                
                # Update account stats
                self.account_service.update_account_stats(account.session_file, success)
                
                # Switch account if needed
                messages_per_account += 1
                if messages_per_account >= max_messages_per_account:
                    await self.account_service.release_client(account)
                    current_account_idx = (current_account_idx + 1) % len(accounts)
                    task.current_account_index = current_account_idx
                    messages_per_account = 0
                    
                    # Account switch delay
                    await asyncio.sleep(config.rate_limit.account_switch_delay)
                else:
                    # Message delay
                    await asyncio.sleep(self._get_delay())
            
            # Completed
            if task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_log.append({
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
            logger.error(f"Task {task_id} failed: {e}")
        
        finally:
            # Clean up
            await self.account_service.release_all_clients()
            if task_id in self._task_locks:
                del self._task_locks[task_id]
            if task_id in self._pause_events:
                del self._pause_events[task_id]
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
        
        logger.info(f"Task {task_id} completed: {task.get_progress_text()}")
        return task

    def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        if task_id in self.active_tasks and task_id in self._pause_events:
            self.active_tasks[task_id].status = TaskStatus.PAUSED
            self._pause_events[task_id].clear()
            logger.info(f"Task {task_id} paused")
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        if task_id in self.active_tasks and task_id in self._pause_events:
            self.active_tasks[task_id].status = TaskStatus.RUNNING
            self._pause_events[task_id].set()
            logger.info(f"Task {task_id} resumed")
            return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = TaskStatus.CANCELLED
            if task_id in self._pause_events:
                self._pause_events[task_id].set()  # Unpause to allow cancellation
            logger.info(f"Task {task_id} cancelled")
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[SendTask]:
        """Get current status of a task."""
        return self.active_tasks.get(task_id)

    def get_all_active_tasks(self) -> List[SendTask]:
        """Get all active tasks."""
        return list(self.active_tasks.values())
