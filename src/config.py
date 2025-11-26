"""Telegram Advertising Bot - Configuration Module"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Main bot configuration."""
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    api_id: int = field(default_factory=lambda: int(os.getenv("API_ID", "0")))
    api_hash: str = field(default_factory=lambda: os.getenv("API_HASH", ""))
    admin_ids: List[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    message_delay_min: int = field(
        default_factory=lambda: int(os.getenv("MESSAGE_DELAY_MIN", "5"))
    )
    message_delay_max: int = field(
        default_factory=lambda: int(os.getenv("MESSAGE_DELAY_MAX", "15"))
    )
    account_switch_delay: int = field(
        default_factory=lambda: int(os.getenv("ACCOUNT_SWITCH_DELAY", "30"))
    )
    max_concurrent_tasks: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
    )
    messages_per_account: int = field(
        default_factory=lambda: int(os.getenv("MESSAGES_PER_ACCOUNT", "50"))
    )
    proxy_test_url: str = field(
        default_factory=lambda: os.getenv("PROXY_TEST_URL", "https://api.telegram.org")
    )


@dataclass
class PathConfig:
    """File path configuration."""
    session_dir: Path = field(
        default_factory=lambda: Path(os.getenv("SESSION_DIR", "data/sessions"))
    )
    proxy_file: Path = field(
        default_factory=lambda: Path(os.getenv("PROXY_FILE", "data/proxies/proxies.json"))
    )
    target_dir: Path = field(
        default_factory=lambda: Path(os.getenv("TARGET_DIR", "data/targets"))
    )
    blacklist_file: Path = field(
        default_factory=lambda: Path(os.getenv("BLACKLIST_FILE", "data/targets/blacklist.txt"))
    )
    log_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LOG_DIR", "logs"))
    )

    def ensure_directories(self):
        """Create all necessary directories."""
        for path in [self.session_dir, self.target_dir, self.log_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self.proxy_file.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    """Complete configuration."""
    bot: BotConfig = field(default_factory=BotConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    paths: PathConfig = field(default_factory=PathConfig)

    def __post_init__(self):
        self.paths.ensure_directories()


# Global configuration instance
config = Config()
