"""Telegram Advertising Bot - Account Management Service"""
import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    SessionPasswordNeeded,
    UserDeactivated,
    UserDeactivatedBan,
)

from ..config import config
from ..models import Account, AccountStatus, Proxy
from ..utils import setup_logging, validate_session_file
from .proxy_service import ProxyService

logger = setup_logging("account_service")


class AccountService:
    """Service for managing Telegram accounts."""

    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.clients: Dict[str, Client] = {}
        self.proxy_service = ProxyService()
        self._load_accounts()

    def _get_accounts_file(self) -> Path:
        """Get path to accounts metadata file."""
        return config.paths.session_dir / "accounts.json"

    def _load_accounts(self):
        """Load accounts metadata from file."""
        accounts_file = self._get_accounts_file()
        if accounts_file.exists():
            with open(accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for session_file, account_data in data.items():
                    self.accounts[session_file] = Account.from_dict(account_data)

    def _save_accounts(self):
        """Save accounts metadata to file."""
        accounts_file = self._get_accounts_file()
        data = {
            session_file: account.to_dict()
            for session_file, account in self.accounts.items()
        }
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def import_session(self, session_path: Path, proxy_id: Optional[str] = None) -> Account:
        """
        Import a session file.
        
        Args:
            session_path: Path to the .session file
            proxy_id: Optional proxy ID to associate with this account
            
        Returns:
            Account object
        """
        if not validate_session_file(session_path):
            raise ValueError(f"Invalid session file: {session_path}")

        # Copy session file to session directory
        dest_path = config.paths.session_dir / session_path.name
        if dest_path != session_path:
            shutil.copy2(session_path, dest_path)

        session_name = session_path.stem
        
        # Create account object
        account = Account(
            session_file=session_path.name,
            proxy_id=proxy_id,
        )
        
        # Validate the session
        account = await self.validate_account(account)
        
        # Save
        self.accounts[session_path.name] = account
        self._save_accounts()
        
        logger.info(f"Imported session: {session_path.name}, status: {account.status.value}")
        return account

    async def validate_account(self, account: Account) -> Account:
        """Validate an account's session."""
        session_path = config.paths.session_dir / account.session_file
        session_name = session_path.stem
        
        # Get proxy if configured
        proxy_dict = None
        if account.proxy_id:
            proxy = self.proxy_service.get_proxy(account.proxy_id)
            if proxy and proxy.is_active:
                proxy_dict = {
                    "scheme": proxy.proxy_type.value,
                    "hostname": proxy.host,
                    "port": proxy.port,
                    "username": proxy.username,
                    "password": proxy.password,
                }

        try:
            client = Client(
                name=str(session_path.with_suffix("")),
                api_id=config.bot.api_id,
                api_hash=config.bot.api_hash,
                workdir=str(config.paths.session_dir),
                proxy=proxy_dict,
            )
            
            await client.start()
            
            # Get user info
            me = await client.get_me()
            account.user_id = me.id
            account.username = me.username
            account.phone = me.phone_number
            account.status = AccountStatus.ACTIVE
            account.can_send_messages = True
            
            await client.stop()
            
            logger.info(f"Account validated: {account.session_file} (user_id: {account.user_id})")
            
        except (AuthKeyUnregistered, UserDeactivated):
            account.status = AccountStatus.INVALID
            account.can_send_messages = False
            logger.warning(f"Account invalid: {account.session_file}")
            
        except UserDeactivatedBan:
            account.status = AccountStatus.BANNED
            account.can_send_messages = False
            logger.warning(f"Account banned: {account.session_file}")
            
        except SessionPasswordNeeded:
            account.status = AccountStatus.RESTRICTED
            account.can_send_messages = False
            logger.warning(f"Account requires 2FA: {account.session_file}")
            
        except FloodWait as e:
            # Account is valid but rate limited
            account.status = AccountStatus.RESTRICTED
            logger.warning(f"Account flood wait: {account.session_file}, wait: {e.value}s")
            
        except Exception as e:
            account.status = AccountStatus.UNKNOWN
            logger.error(f"Error validating account {account.session_file}: {e}")

        return account

    async def get_client(self, account: Account) -> Optional[Client]:
        """Get or create a client for an account."""
        session_file = account.session_file
        
        if session_file in self.clients:
            client = self.clients[session_file]
            if client.is_connected:
                return client
        
        session_path = config.paths.session_dir / session_file
        session_name = session_path.stem
        
        # Get proxy if configured
        proxy_dict = None
        if account.proxy_id:
            proxy = self.proxy_service.get_proxy(account.proxy_id)
            if proxy and proxy.is_active:
                proxy_dict = {
                    "scheme": proxy.proxy_type.value,
                    "hostname": proxy.host,
                    "port": proxy.port,
                    "username": proxy.username,
                    "password": proxy.password,
                }

        try:
            client = Client(
                name=str(session_path.with_suffix("")),
                api_id=config.bot.api_id,
                api_hash=config.bot.api_hash,
                workdir=str(config.paths.session_dir),
                proxy=proxy_dict,
            )
            
            await client.start()
            self.clients[session_file] = client
            return client
            
        except Exception as e:
            logger.error(f"Failed to create client for {session_file}: {e}")
            return None

    async def release_client(self, account: Account):
        """Release a client connection."""
        session_file = account.session_file
        if session_file in self.clients:
            client = self.clients[session_file]
            try:
                await client.stop()
            except Exception:
                pass
            del self.clients[session_file]

    async def release_all_clients(self):
        """Release all client connections."""
        for session_file, client in list(self.clients.items()):
            try:
                await client.stop()
            except Exception:
                pass
        self.clients.clear()

    def get_account(self, session_file: str) -> Optional[Account]:
        """Get account by session file name."""
        return self.accounts.get(session_file)

    def get_active_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return [
            account for account in self.accounts.values()
            if account.status == AccountStatus.ACTIVE and account.can_send_messages
        ]

    def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        return list(self.accounts.values())

    def remove_account(self, session_file: str) -> bool:
        """Remove an account."""
        if session_file in self.accounts:
            # Remove session file
            session_path = config.paths.session_dir / session_file
            if session_path.exists():
                session_path.unlink()
            
            # Remove from accounts
            del self.accounts[session_file]
            self._save_accounts()
            
            logger.info(f"Removed account: {session_file}")
            return True
        return False

    def set_account_proxy(self, session_file: str, proxy_id: Optional[str]) -> bool:
        """Set proxy for an account."""
        if session_file in self.accounts:
            self.accounts[session_file].proxy_id = proxy_id
            self._save_accounts()
            return True
        return False

    def update_account_stats(self, session_file: str, success: bool = True):
        """Update account statistics after sending."""
        if session_file in self.accounts:
            account = self.accounts[session_file]
            account.last_used = datetime.now()
            account.messages_sent += 1
            if not success:
                account.errors += 1
            self._save_accounts()

    async def validate_all_accounts(self):
        """Validate all accounts."""
        for session_file, account in self.accounts.items():
            await self.validate_account(account)
        self._save_accounts()
