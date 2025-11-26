"""Telegram Advertising Bot - Utility Functions"""
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

from ..config import config


def setup_logging(name: str = "telegram_ad_bot") -> logging.Logger:
    """Set up logging configuration."""
    log_dir = config.paths.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def parse_target_identifier(identifier: str) -> Tuple[str, str]:
    """
    Parse target identifier and determine its type.
    
    Returns:
        Tuple of (cleaned_identifier, identifier_type)
    """
    identifier = identifier.strip()
    
    # Check if it's a user ID (numeric)
    if identifier.isdigit():
        return identifier, "user_id"
    
    # Check if it's a phone number
    phone_pattern = r"^\+?\d{10,15}$"
    if re.match(phone_pattern, identifier.replace(" ", "").replace("-", "")):
        return identifier.replace(" ", "").replace("-", ""), "phone"
    
    # Otherwise treat as username (remove @ if present)
    if identifier.startswith("@"):
        identifier = identifier[1:]
    
    return identifier, "username"


def load_target_list(file_path: Path) -> List[Tuple[str, str]]:
    """
    Load target list from file.
    
    Returns:
        List of tuples (identifier, identifier_type)
    """
    targets = []
    if not file_path.exists():
        return targets
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                identifier, id_type = parse_target_identifier(line)
                targets.append((identifier, id_type))
    
    return targets


def load_blacklist() -> Set[str]:
    """Load blacklist from file."""
    blacklist = set()
    blacklist_file = config.paths.blacklist_file
    
    if blacklist_file.exists():
        with open(blacklist_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    # Remove @ prefix if present
                    if line.startswith("@"):
                        line = line[1:]
                    blacklist.add(line)
    
    return blacklist


def add_to_blacklist(identifier: str) -> bool:
    """Add identifier to blacklist."""
    blacklist_file = config.paths.blacklist_file
    blacklist_file.parent.mkdir(parents=True, exist_ok=True)
    
    identifier = identifier.strip().lower()
    if identifier.startswith("@"):
        identifier = identifier[1:]
    
    # Check if already in blacklist
    existing = load_blacklist()
    if identifier in existing:
        return False
    
    with open(blacklist_file, "a", encoding="utf-8") as f:
        f.write(f"{identifier}\n")
    
    return True


def is_blacklisted(identifier: str) -> bool:
    """Check if identifier is blacklisted."""
    identifier = identifier.strip().lower()
    if identifier.startswith("@"):
        identifier = identifier[1:]
    
    blacklist = load_blacklist()
    return identifier in blacklist


def render_template(template: str, variables: dict) -> str:
    """
    Render message template with variables.
    
    Supported variables:
    - {username}: Target username
    - {user_id}: Target user ID
    - {first_name}: Target first name
    - {last_name}: Target last name
    - {date}: Current date
    - {time}: Current time
    """
    # Add default variables
    now = datetime.now()
    variables.setdefault("date", now.strftime("%Y-%m-%d"))
    variables.setdefault("time", now.strftime("%H:%M"))
    
    # Replace variables
    for key, value in variables.items():
        if value is not None:
            template = template.replace(f"{{{key}}}", str(value))
    
    return template


def deduplicate_targets(targets: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Remove duplicate targets while preserving order."""
    seen = set()
    result = []
    for identifier, id_type in targets:
        key = f"{id_type}:{identifier.lower()}"
        if key not in seen:
            seen.add(key)
            result.append((identifier, id_type))
    return result


def filter_blacklisted(targets: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Filter out blacklisted targets."""
    blacklist = load_blacklist()
    return [
        (identifier, id_type)
        for identifier, id_type in targets
        if identifier.lower() not in blacklist
    ]


def validate_session_file(file_path: Path) -> bool:
    """Validate that a session file exists and is readable."""
    return file_path.exists() and file_path.is_file() and file_path.suffix == ".session"


def get_session_files() -> List[Path]:
    """Get all session files from the session directory."""
    session_dir = config.paths.session_dir
    if not session_dir.exists():
        return []
    return list(session_dir.glob("*.session"))


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
