"""Telegram Advertising Bot - Configuration Module"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
from dotenv import load_dotenv

load_dotenv()

# Module-level logger for config parsing
_config_logger = logging.getLogger("config")


def _parse_admin_ids() -> Set[int]:
    """
    Parse ADMIN_IDS from environment variable.
    
    Supports comma-separated list of user IDs with optional spaces.
    Logs clear error messages for invalid values.
    
    Returns:
        Set of valid admin user IDs.
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "").strip()
    if not admin_ids_str:
        _config_logger.warning(
            "ADMIN_IDS is empty or not set. No admin users configured. "
            "Set ADMIN_IDS in .env file with comma-separated Telegram user IDs."
        )
        return set()
    
    admin_ids: Set[int] = set()
    raw_ids = admin_ids_str.split(",")
    
    for raw_id in raw_ids:
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            user_id = int(raw_id)
            if user_id <= 0:
                _config_logger.error(
                    f"Invalid admin ID '{raw_id}': must be a positive integer. Skipping."
                )
                continue
            admin_ids.add(user_id)
        except ValueError:
            _config_logger.error(
                f"Failed to parse admin ID '{raw_id}': not a valid integer. "
                "Use numeric Telegram user IDs, not usernames. Skipping."
            )
    
    if admin_ids:
        _config_logger.info(f"Loaded {len(admin_ids)} admin ID(s): {sorted(admin_ids)}")
    else:
        _config_logger.warning(
            f"No valid admin IDs parsed from ADMIN_IDS='{admin_ids_str}'. "
            "Ensure you use numeric Telegram user IDs separated by commas."
        )
    
    return admin_ids


@dataclass
class BotConfig:
    """Main bot configuration."""
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    api_id: int = field(default_factory=lambda: int(os.getenv("API_ID", "0")))
    api_hash: str = field(default_factory=lambda: os.getenv("API_HASH", ""))
    admin_ids: Set[int] = field(default_factory=_parse_admin_ids)


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
