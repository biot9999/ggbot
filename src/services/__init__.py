"""Telegram Advertising Bot - Services Package"""
from .account_service import AccountService
from .proxy_service import ProxyService
from .sending_service import SendingService
from .target_service import TargetService
from .task_service import TaskService
from .template_service import TemplateService

__all__ = [
    "AccountService",
    "ProxyService",
    "SendingService",
    "TargetService",
    "TaskService",
    "TemplateService",
]
