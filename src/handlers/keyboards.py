"""Telegram Advertising Bot - Keyboard Layouts"""
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 Accounts", callback_data="menu_accounts"),
            InlineKeyboardButton("👥 Targets", callback_data="menu_targets"),
        ],
        [
            InlineKeyboardButton("📝 Templates", callback_data="menu_templates"),
            InlineKeyboardButton("🌐 Proxies", callback_data="menu_proxies"),
        ],
        [
            InlineKeyboardButton("📤 Tasks", callback_data="menu_tasks"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
    ])


def accounts_menu_keyboard() -> InlineKeyboardMarkup:
    """Accounts management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Session", callback_data="account_upload")],
        [InlineKeyboardButton("📋 List Accounts", callback_data="account_list")],
        [InlineKeyboardButton("✅ Validate All", callback_data="account_validate_all")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def account_detail_keyboard(session_file: str) -> InlineKeyboardMarkup:
    """Account detail actions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Validate", callback_data=f"account_validate:{session_file}")],
        [InlineKeyboardButton("🌐 Set Proxy", callback_data=f"account_proxy:{session_file}")],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"account_delete:{session_file}")],
        [InlineKeyboardButton("🔙 Back", callback_data="account_list")],
    ])


def targets_menu_keyboard() -> InlineKeyboardMarkup:
    """Targets management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Target List", callback_data="target_upload")],
        [InlineKeyboardButton("📋 List Target Lists", callback_data="target_list")],
        [InlineKeyboardButton("🚫 Manage Blacklist", callback_data="target_blacklist")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def target_list_detail_keyboard(list_name: str) -> InlineKeyboardMarkup:
    """Target list detail actions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics", callback_data=f"target_stats:{list_name}")],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"target_delete:{list_name}")],
        [InlineKeyboardButton("🔙 Back", callback_data="target_list")],
    ])


def blacklist_menu_keyboard() -> InlineKeyboardMarkup:
    """Blacklist management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Blacklist", callback_data="blacklist_add")],
        [InlineKeyboardButton("📋 View Blacklist", callback_data="blacklist_view")],
        [InlineKeyboardButton("🗑 Clear Blacklist", callback_data="blacklist_clear")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_targets")],
    ])


def templates_menu_keyboard() -> InlineKeyboardMarkup:
    """Templates management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Create Text Template", callback_data="template_create_text")],
        [InlineKeyboardButton("📷 Create Media Template", callback_data="template_create_media")],
        [InlineKeyboardButton("📢 Create Forward Template", callback_data="template_create_forward")],
        [InlineKeyboardButton("📋 List Templates", callback_data="template_list")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def template_detail_keyboard(template_id: str) -> InlineKeyboardMarkup:
    """Template detail actions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Preview", callback_data=f"template_preview:{template_id}")],
        [InlineKeyboardButton("✏️ Edit", callback_data=f"template_edit:{template_id}")],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"template_delete:{template_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="template_list")],
    ])


def proxies_menu_keyboard() -> InlineKeyboardMarkup:
    """Proxies management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Proxy", callback_data="proxy_add")],
        [InlineKeyboardButton("📤 Import Proxies", callback_data="proxy_import")],
        [InlineKeyboardButton("📋 List Proxies", callback_data="proxy_list")],
        [InlineKeyboardButton("🔄 Test All Proxies", callback_data="proxy_test_all")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def proxy_detail_keyboard(proxy_id: str) -> InlineKeyboardMarkup:
    """Proxy detail actions."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Test", callback_data=f"proxy_test:{proxy_id}")],
        [InlineKeyboardButton("✏️ Edit", callback_data=f"proxy_edit:{proxy_id}")],
        [
            InlineKeyboardButton("✅ Enable", callback_data=f"proxy_enable:{proxy_id}"),
            InlineKeyboardButton("❌ Disable", callback_data=f"proxy_disable:{proxy_id}"),
        ],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"proxy_delete:{proxy_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="proxy_list")],
    ])


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    """Tasks management menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Task", callback_data="task_create")],
        [InlineKeyboardButton("📋 List Tasks", callback_data="task_list")],
        [InlineKeyboardButton("▶️ Running Tasks", callback_data="task_running")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def task_detail_keyboard(task_id: str, status: str) -> InlineKeyboardMarkup:
    """Task detail actions based on status."""
    buttons = []
    
    if status == "pending":
        buttons.append([InlineKeyboardButton("▶️ Start", callback_data=f"task_start:{task_id}")])
    elif status == "running":
        buttons.append([InlineKeyboardButton("⏸ Pause", callback_data=f"task_pause:{task_id}")])
        buttons.append([InlineKeyboardButton("⏹ Cancel", callback_data=f"task_cancel:{task_id}")])
    elif status == "paused":
        buttons.append([InlineKeyboardButton("▶️ Resume", callback_data=f"task_resume:{task_id}")])
        buttons.append([InlineKeyboardButton("⏹ Cancel", callback_data=f"task_cancel:{task_id}")])
    
    if status in ["completed", "cancelled", "failed"]:
        buttons.append([InlineKeyboardButton("📊 Export Report", callback_data=f"task_report:{task_id}")])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"task_detail:{task_id}")])
    buttons.append([InlineKeyboardButton("🗑 Delete", callback_data=f"task_delete:{task_id}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="task_list")])
    
    return InlineKeyboardMarkup(buttons)


def task_create_accounts_keyboard(accounts: list, selected: list) -> InlineKeyboardMarkup:
    """Account selection for task creation."""
    buttons = []
    for acc in accounts:
        check = "✅" if acc.session_file in selected else "⬜"
        buttons.append([
            InlineKeyboardButton(
                f"{check} {acc.username or acc.session_file}",
                callback_data=f"task_toggle_account:{acc.session_file}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton("✅ Select All", callback_data="task_select_all_accounts"),
        InlineKeyboardButton("❌ Clear All", callback_data="task_clear_all_accounts"),
    ])
    buttons.append([InlineKeyboardButton("➡️ Next", callback_data="task_create_next")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="task_list")])
    
    return InlineKeyboardMarkup(buttons)


def task_create_targets_keyboard(target_lists: dict) -> InlineKeyboardMarkup:
    """Target list selection for task creation."""
    buttons = []
    for list_name, count in target_lists.items():
        buttons.append([
            InlineKeyboardButton(
                f"📋 {list_name} ({count})",
                callback_data=f"task_select_targets:{list_name}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="task_create")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="task_list")])
    
    return InlineKeyboardMarkup(buttons)


def task_create_templates_keyboard(templates: list) -> InlineKeyboardMarkup:
    """Template selection for task creation."""
    buttons = []
    for template in templates:
        buttons.append([
            InlineKeyboardButton(
                f"📝 {template.name}",
                callback_data=f"task_select_template:{template.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="task_create_targets")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="task_list")])
    
    return InlineKeyboardMarkup(buttons)


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Settings menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ Rate Limits", callback_data="settings_rate_limits")],
        [InlineKeyboardButton("📊 Statistics", callback_data="settings_stats")],
        [InlineKeyboardButton("📋 Logs", callback_data="settings_logs")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")],
    ])


def confirm_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}:{item_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action}:{item_id}"),
        ],
    ])


def back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=callback_data)],
    ])
