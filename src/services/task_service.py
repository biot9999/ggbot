"""Telegram Advertising Bot - Task Management Service"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from ..config import config
from ..models import SendTask, TaskStatus
from ..utils import setup_logging
from .sending_service import SendingService

logger = setup_logging("task_service")


class TaskService:
    """Service for managing and scheduling tasks."""

    def __init__(self, sending_service: SendingService):
        self.sending_service = sending_service
        self.tasks: Dict[str, SendTask] = {}
        self.scheduler = AsyncIOScheduler()
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._load_tasks()

    def _get_tasks_file(self) -> Path:
        """Get path to tasks file."""
        return config.paths.target_dir.parent / "tasks.json"

    def _load_tasks(self):
        """Load tasks from file."""
        tasks_file = self._get_tasks_file()
        if tasks_file.exists():
            with open(tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for task_id, task_data in data.items():
                    self.tasks[task_id] = SendTask.from_dict(task_data)
        logger.info(f"Loaded {len(self.tasks)} tasks")

    def _save_tasks(self):
        """Save tasks to file."""
        tasks_file = self._get_tasks_file()
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            task_id: task.to_dict()
            for task_id, task in self.tasks.items()
        }
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_task(
        self,
        name: str,
        template_id: str,
        target_list_file: str,
        accounts: List[str],
        scheduled_time: Optional[datetime] = None,
    ) -> SendTask:
        """Create a new task."""
        task_id = str(uuid.uuid4())[:8]
        task = SendTask(
            id=task_id,
            name=name,
            template_id=template_id,
            target_list_file=target_list_file,
            accounts=accounts,
            scheduled_time=scheduled_time,
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        # Schedule if scheduled_time is set
        if scheduled_time and scheduled_time > datetime.now():
            self._schedule_task(task)
        
        logger.info(f"Created task: {task_id} ({name})")
        return task

    def _schedule_task(self, task: SendTask):
        """Schedule a task for later execution."""
        if not task.scheduled_time:
            return
        
        job_id = f"task_{task.id}"
        self.scheduler.add_job(
            self._run_scheduled_task,
            trigger=DateTrigger(run_date=task.scheduled_time),
            id=job_id,
            args=[task.id],
            replace_existing=True,
        )
        logger.info(f"Scheduled task {task.id} for {task.scheduled_time}")

    async def _run_scheduled_task(self, task_id: str):
        """Run a scheduled task."""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            await self.start_task(task_id)

    async def start_task(self, task_id: str) -> Optional[SendTask]:
        """Start a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.PAUSED]:
            logger.warning(f"Cannot start task {task_id} with status {task.status}")
            return None
        
        # Run in background
        asyncio.create_task(self._execute_task(task))
        
        return task

    async def _execute_task(self, task: SendTask):
        """Execute a task and handle progress updates."""
        try:
            await self.sending_service.execute_task(task)
        finally:
            self._save_tasks()
            await self._notify_progress(task.id, task)

    def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        result = self.sending_service.pause_task(task_id)
        if result:
            self.tasks[task_id].status = TaskStatus.PAUSED
            self._save_tasks()
        return result

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        result = self.sending_service.resume_task(task_id)
        if result:
            self.tasks[task_id].status = TaskStatus.RUNNING
            self._save_tasks()
        return result

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        # Cancel scheduled job if exists
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        result = self.sending_service.cancel_task(task_id)
        if result:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            self._save_tasks()
        return result

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id not in self.tasks:
            return False
        
        # Cancel if running
        self.cancel_task(task_id)
        
        del self.tasks[task_id]
        self._save_tasks()
        logger.info(f"Deleted task: {task_id}")
        return True

    def get_task(self, task_id: str) -> Optional[SendTask]:
        """Get a task by ID."""
        # Check active tasks first for live status
        active_task = self.sending_service.get_task_status(task_id)
        if active_task:
            return active_task
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[SendTask]:
        """Get all tasks."""
        return list(self.tasks.values())

    def get_pending_tasks(self) -> List[SendTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]

    def get_running_tasks(self) -> List[SendTask]:
        """Get all running tasks."""
        return self.sending_service.get_all_active_tasks()

    def register_progress_callback(self, task_id: str, callback: Callable):
        """Register a callback for task progress updates."""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)

    def unregister_progress_callback(self, task_id: str, callback: Callable):
        """Unregister a progress callback."""
        if task_id in self._progress_callbacks:
            self._progress_callbacks[task_id].remove(callback)

    async def _notify_progress(self, task_id: str, task: SendTask):
        """Notify all registered callbacks of progress."""
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    await callback(task)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

    def start_scheduler(self):
        """Start the task scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Task scheduler started")

    def stop_scheduler(self):
        """Stop the task scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler stopped")

    def export_report(self, task_id: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Export a task report."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if output_path is None:
            reports_dir = config.paths.target_dir.parent / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            output_path = reports_dir / f"report_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        report_lines = [
            f"Task Report: {task.name}",
            f"Task ID: {task.id}",
            f"Status: {task.status.value}",
            f"Created: {task.created_at.isoformat()}",
            f"Started: {task.started_at.isoformat() if task.started_at else 'N/A'}",
            f"Completed: {task.completed_at.isoformat() if task.completed_at else 'N/A'}",
            "",
            "=== Statistics ===",
            f"Total Targets: {task.total_targets}",
            f"Sent: {task.sent_count}",
            f"Success: {task.success_count}",
            f"Failed: {task.failed_count}",
            f"Skipped: {task.skipped_count}",
            "",
        ]
        
        if task.error_log:
            report_lines.append("=== Errors ===")
            for error in task.error_log:
                report_lines.append(f"- {error.get('target', 'Unknown')}: {error.get('error', 'Unknown error')}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        
        logger.info(f"Exported report for task {task_id} to {output_path}")
        return output_path
