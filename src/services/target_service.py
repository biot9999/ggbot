"""Telegram Advertising Bot - Target User Management Service"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import uuid

from ..config import config
from ..models import TargetUser
from ..utils import (
    add_to_blacklist,
    deduplicate_targets,
    filter_blacklisted,
    is_blacklisted,
    load_blacklist,
    load_target_list,
    setup_logging,
)

logger = setup_logging("target_service")


class TargetService:
    """Service for managing target users."""

    def __init__(self):
        self.target_lists: Dict[str, List[TargetUser]] = {}
        self._load_target_lists()

    def _get_metadata_file(self) -> Path:
        """Get path to target lists metadata file."""
        return config.paths.target_dir / "target_lists.json"

    def _load_target_lists(self):
        """Load target lists metadata."""
        metadata_file = self._get_metadata_file()
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for list_name, targets_data in data.items():
                    self.target_lists[list_name] = [
                        TargetUser(
                            identifier=t["identifier"],
                            identifier_type=t["identifier_type"],
                            user_id=t.get("user_id"),
                            username=t.get("username"),
                            is_valid=t.get("is_valid", True),
                            error_message=t.get("error_message"),
                        )
                        for t in targets_data
                    ]
        logger.info(f"Loaded {len(self.target_lists)} target lists")

    def _save_target_lists(self):
        """Save target lists metadata."""
        metadata_file = self._get_metadata_file()
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            list_name: [t.to_dict() for t in targets]
            for list_name, targets in self.target_lists.items()
        }
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_from_file(self, file_path: Path, list_name: Optional[str] = None) -> Tuple[str, int, int]:
        """
        Import targets from a text file.
        
        Args:
            file_path: Path to the .txt file
            list_name: Optional name for the list (defaults to filename)
            
        Returns:
            Tuple of (list_name, total_count, unique_count)
        """
        if list_name is None:
            list_name = file_path.stem
        
        # Load targets from file
        raw_targets = load_target_list(file_path)
        total_count = len(raw_targets)
        
        # Deduplicate
        unique_targets = deduplicate_targets(raw_targets)
        
        # Filter blacklisted
        filtered_targets = filter_blacklisted(unique_targets)
        
        # Convert to TargetUser objects
        target_users = [
            TargetUser(identifier=identifier, identifier_type=id_type)
            for identifier, id_type in filtered_targets
        ]
        
        # Save to targets directory
        dest_path = config.paths.target_dir / f"{list_name}.txt"
        with open(dest_path, "w", encoding="utf-8") as f:
            for target in target_users:
                f.write(f"{target.identifier}\n")
        
        self.target_lists[list_name] = target_users
        self._save_target_lists()
        
        logger.info(
            f"Imported target list '{list_name}': {total_count} total, "
            f"{len(target_users)} unique (after dedup and blacklist filter)"
        )
        
        return list_name, total_count, len(target_users)

    def get_target_list(self, list_name: str) -> Optional[List[TargetUser]]:
        """Get a target list by name."""
        return self.target_lists.get(list_name)

    def get_all_lists(self) -> Dict[str, int]:
        """Get all target lists with their counts."""
        return {name: len(targets) for name, targets in self.target_lists.items()}

    def remove_target_list(self, list_name: str) -> bool:
        """Remove a target list."""
        if list_name in self.target_lists:
            # Remove file
            file_path = config.paths.target_dir / f"{list_name}.txt"
            if file_path.exists():
                file_path.unlink()
            
            del self.target_lists[list_name]
            self._save_target_lists()
            
            logger.info(f"Removed target list: {list_name}")
            return True
        return False

    def add_to_blacklist(self, identifier: str) -> bool:
        """Add a user to the blacklist."""
        result = add_to_blacklist(identifier)
        if result:
            # Update existing target lists
            for list_name, targets in self.target_lists.items():
                for target in targets:
                    if target.identifier.lower() == identifier.lower():
                        target.is_valid = False
                        target.error_message = "Blacklisted"
            self._save_target_lists()
            logger.info(f"Added to blacklist: {identifier}")
        return result

    def get_blacklist(self) -> Set[str]:
        """Get the current blacklist."""
        return load_blacklist()

    def clear_blacklist(self) -> int:
        """Clear the blacklist."""
        blacklist_file = config.paths.blacklist_file
        count = len(load_blacklist())
        if blacklist_file.exists():
            blacklist_file.unlink()
        logger.info(f"Cleared blacklist ({count} entries)")
        return count

    def is_blacklisted(self, identifier: str) -> bool:
        """Check if a user is blacklisted."""
        return is_blacklisted(identifier)

    def update_target_status(
        self,
        list_name: str,
        identifier: str,
        is_valid: bool,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Update a target's status after validation."""
        if list_name in self.target_lists:
            for target in self.target_lists[list_name]:
                if target.identifier.lower() == identifier.lower():
                    target.is_valid = is_valid
                    if user_id:
                        target.user_id = user_id
                    if username:
                        target.username = username
                    if error_message:
                        target.error_message = error_message
                    break
            self._save_target_lists()

    def get_valid_targets(self, list_name: str) -> List[TargetUser]:
        """Get valid (not blacklisted, not errored) targets from a list."""
        targets = self.target_lists.get(list_name, [])
        return [t for t in targets if t.is_valid]

    def get_stats(self, list_name: str) -> Dict[str, int]:
        """Get statistics for a target list."""
        targets = self.target_lists.get(list_name, [])
        return {
            "total": len(targets),
            "valid": len([t for t in targets if t.is_valid]),
            "invalid": len([t for t in targets if not t.is_valid]),
            "usernames": len([t for t in targets if t.identifier_type == "username"]),
            "user_ids": len([t for t in targets if t.identifier_type == "user_id"]),
            "phones": len([t for t in targets if t.identifier_type == "phone"]),
        }
