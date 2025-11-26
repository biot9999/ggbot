"""Telegram Advertising Bot - Data Models"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AccountStatus(Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    RESTRICTED = "restricted"
    BANNED = "banned"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProxyType(Enum):
    """Proxy type enumeration."""
    HTTP = "http"
    SOCKS5 = "socks5"


@dataclass
class Account:
    """Telegram account model."""
    session_file: str
    phone: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    status: AccountStatus = AccountStatus.UNKNOWN
    can_send_messages: bool = True
    proxy_id: Optional[str] = None
    last_used: Optional[datetime] = None
    messages_sent: int = 0
    errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_file": self.session_file,
            "phone": self.phone,
            "user_id": self.user_id,
            "username": self.username,
            "status": self.status.value,
            "can_send_messages": self.can_send_messages,
            "proxy_id": self.proxy_id,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "messages_sent": self.messages_sent,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        """Create from dictionary."""
        return cls(
            session_file=data["session_file"],
            phone=data.get("phone"),
            user_id=data.get("user_id"),
            username=data.get("username"),
            status=AccountStatus(data.get("status", "unknown")),
            can_send_messages=data.get("can_send_messages", True),
            proxy_id=data.get("proxy_id"),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            messages_sent=data.get("messages_sent", 0),
            errors=data.get("errors", 0),
        )


@dataclass
class TargetUser:
    """Target user model."""
    identifier: str  # username, user_id, or phone
    identifier_type: str  # "username", "user_id", "phone"
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "identifier": self.identifier,
            "identifier_type": self.identifier_type,
            "user_id": self.user_id,
            "username": self.username,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
        }


@dataclass
class Proxy:
    """Proxy configuration model."""
    id: str
    proxy_type: ProxyType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True
    last_tested: Optional[datetime] = None
    is_working: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "proxy_type": self.proxy_type.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "is_active": self.is_active,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "is_working": self.is_working,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proxy":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            proxy_type=ProxyType(data["proxy_type"]),
            host=data["host"],
            port=data["port"],
            username=data.get("username"),
            password=data.get("password"),
            is_active=data.get("is_active", True),
            last_tested=datetime.fromisoformat(data["last_tested"]) if data.get("last_tested") else None,
            is_working=data.get("is_working", False),
        )

    def get_connection_string(self) -> str:
        """Get proxy connection string."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"


@dataclass
class MessageTemplate:
    """Message template model."""
    id: str
    name: str
    text: Optional[str] = None
    media_path: Optional[str] = None
    media_type: Optional[str] = None  # "photo", "document", "video"
    buttons: Optional[List[Dict[str, str]]] = None  # [{text, url}]
    forward_from_channel: Optional[str] = None
    forward_message_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "text": self.text,
            "media_path": self.media_path,
            "media_type": self.media_type,
            "buttons": self.buttons,
            "forward_from_channel": self.forward_from_channel,
            "forward_message_id": self.forward_message_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageTemplate":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            text=data.get("text"),
            media_path=data.get("media_path"),
            media_type=data.get("media_type"),
            buttons=data.get("buttons"),
            forward_from_channel=data.get("forward_from_channel"),
            forward_message_id=data.get("forward_message_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


@dataclass
class SendTask:
    """Sending task model."""
    id: str
    name: str
    template_id: str
    target_list_file: str
    accounts: List[str]  # session file names
    status: TaskStatus = TaskStatus.PENDING
    total_targets: int = 0
    sent_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    current_target_index: int = 0
    current_account_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_time: Optional[datetime] = None
    error_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "template_id": self.template_id,
            "target_list_file": self.target_list_file,
            "accounts": self.accounts,
            "status": self.status.value,
            "total_targets": self.total_targets,
            "sent_count": self.sent_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "current_target_index": self.current_target_index,
            "current_account_index": self.current_account_index,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "error_log": self.error_log,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SendTask":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            template_id=data["template_id"],
            target_list_file=data["target_list_file"],
            accounts=data["accounts"],
            status=TaskStatus(data.get("status", "pending")),
            total_targets=data.get("total_targets", 0),
            sent_count=data.get("sent_count", 0),
            success_count=data.get("success_count", 0),
            failed_count=data.get("failed_count", 0),
            skipped_count=data.get("skipped_count", 0),
            current_target_index=data.get("current_target_index", 0),
            current_account_index=data.get("current_account_index", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]) if data.get("scheduled_time") else None,
            error_log=data.get("error_log", []),
        )

    def get_progress_text(self) -> str:
        """Get human-readable progress text."""
        if self.total_targets == 0:
            return "No targets"
        progress = (self.sent_count / self.total_targets) * 100
        return (
            f"📊 Progress: {progress:.1f}%\n"
            f"📤 Sent: {self.sent_count}/{self.total_targets}\n"
            f"✅ Success: {self.success_count}\n"
            f"❌ Failed: {self.failed_count}\n"
            f"⏭️ Skipped: {self.skipped_count}"
        )
