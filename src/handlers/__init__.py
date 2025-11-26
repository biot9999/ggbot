"""Telegram Advertising Bot - Handlers Package"""
from .account_handlers import AccountHandlers
from .keyboards import (
    accounts_menu_keyboard,
    back_keyboard,
    confirm_keyboard,
    main_menu_keyboard,
    proxies_menu_keyboard,
    settings_menu_keyboard,
    targets_menu_keyboard,
    tasks_menu_keyboard,
    templates_menu_keyboard,
)
from .proxy_handlers import ProxyHandlers
from .target_handlers import TargetHandlers
from .task_handlers import TaskHandlers
from .template_handlers import TemplateHandlers

__all__ = [
    "AccountHandlers",
    "ProxyHandlers",
    "TargetHandlers",
    "TaskHandlers",
    "TemplateHandlers",
    "accounts_menu_keyboard",
    "back_keyboard",
    "confirm_keyboard",
    "main_menu_keyboard",
    "proxies_menu_keyboard",
    "settings_menu_keyboard",
    "targets_menu_keyboard",
    "tasks_menu_keyboard",
    "templates_menu_keyboard",
]
