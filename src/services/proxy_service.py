"""Telegram Advertising Bot - Proxy Management Service"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

import aiohttp
from aiohttp_socks import ProxyConnector

from ..config import config
from ..models import Proxy, ProxyType
from ..utils import setup_logging

logger = setup_logging("proxy_service")


class ProxyService:
    """Service for managing proxies."""

    def __init__(self):
        self.proxies: Dict[str, Proxy] = {}
        self._current_index = 0
        self._load_proxies()

    def _load_proxies(self):
        """Load proxies from file."""
        proxy_file = config.paths.proxy_file
        if proxy_file.exists():
            with open(proxy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for proxy_id, proxy_data in data.items():
                    self.proxies[proxy_id] = Proxy.from_dict(proxy_data)
        logger.info(f"Loaded {len(self.proxies)} proxies")

    def _save_proxies(self):
        """Save proxies to file."""
        proxy_file = config.paths.proxy_file
        proxy_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            proxy_id: proxy.to_dict()
            for proxy_id, proxy in self.proxies.items()
        }
        with open(proxy_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_proxy(
        self,
        proxy_type: ProxyType,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Proxy:
        """Add a new proxy."""
        proxy_id = str(uuid.uuid4())[:8]
        proxy = Proxy(
            id=proxy_id,
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self.proxies[proxy_id] = proxy
        self._save_proxies()
        logger.info(f"Added proxy: {proxy_id} ({host}:{port})")
        return proxy

    def update_proxy(
        self,
        proxy_id: str,
        proxy_type: Optional[ProxyType] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Proxy]:
        """Update an existing proxy."""
        if proxy_id not in self.proxies:
            return None
        
        proxy = self.proxies[proxy_id]
        if proxy_type is not None:
            proxy.proxy_type = proxy_type
        if host is not None:
            proxy.host = host
        if port is not None:
            proxy.port = port
        if username is not None:
            proxy.username = username
        if password is not None:
            proxy.password = password
        if is_active is not None:
            proxy.is_active = is_active
        
        self._save_proxies()
        logger.info(f"Updated proxy: {proxy_id}")
        return proxy

    def remove_proxy(self, proxy_id: str) -> bool:
        """Remove a proxy."""
        if proxy_id in self.proxies:
            del self.proxies[proxy_id]
            self._save_proxies()
            logger.info(f"Removed proxy: {proxy_id}")
            return True
        return False

    def get_proxy(self, proxy_id: str) -> Optional[Proxy]:
        """Get a proxy by ID."""
        return self.proxies.get(proxy_id)

    def get_all_proxies(self) -> List[Proxy]:
        """Get all proxies."""
        return list(self.proxies.values())

    def get_active_proxies(self) -> List[Proxy]:
        """Get all active proxies."""
        return [p for p in self.proxies.values() if p.is_active and p.is_working]

    def get_next_proxy(self) -> Optional[Proxy]:
        """Get next proxy in rotation."""
        active_proxies = self.get_active_proxies()
        if not active_proxies:
            return None
        
        proxy = active_proxies[self._current_index % len(active_proxies)]
        self._current_index += 1
        return proxy

    async def test_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        """Test if a proxy is working."""
        try:
            proxy_url = proxy.get_connection_string()
            
            connector = ProxyConnector.from_url(proxy_url)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    "https://api.telegram.org",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    is_working = response.status == 200 or response.status == 404
            
            proxy.is_working = is_working
            proxy.last_tested = datetime.now()
            self._save_proxies()
            
            logger.info(f"Proxy test {proxy.id}: {'OK' if is_working else 'FAILED'}")
            return is_working
            
        except Exception as e:
            proxy.is_working = False
            proxy.last_tested = datetime.now()
            self._save_proxies()
            logger.warning(f"Proxy test {proxy.id} failed: {e}")
            return False

    async def test_all_proxies(self) -> Dict[str, bool]:
        """Test all proxies."""
        results = {}
        for proxy_id, proxy in self.proxies.items():
            results[proxy_id] = await self.test_proxy(proxy)
            await asyncio.sleep(1)  # Avoid overwhelming
        return results

    def parse_proxy_string(self, proxy_string: str) -> Optional[Proxy]:
        """
        Parse a proxy from string format.
        
        Supported formats:
        - scheme://host:port
        - scheme://user:pass@host:port
        - host:port:user:pass (assumes socks5)
        """
        proxy_string = proxy_string.strip()
        
        try:
            # Try URL format
            if "://" in proxy_string:
                parts = proxy_string.split("://")
                scheme = parts[0].lower()
                rest = parts[1]
                
                proxy_type = ProxyType.SOCKS5 if "socks" in scheme else ProxyType.HTTP
                
                if "@" in rest:
                    auth, host_port = rest.rsplit("@", 1)
                    username, password = auth.split(":", 1)
                else:
                    host_port = rest
                    username = password = None
                
                host, port = host_port.split(":")
                port = int(port)
                
            else:
                # Try host:port:user:pass format
                parts = proxy_string.split(":")
                if len(parts) == 2:
                    host, port = parts
                    username = password = None
                elif len(parts) == 4:
                    host, port, username, password = parts
                else:
                    return None
                
                port = int(port)
                proxy_type = ProxyType.SOCKS5
            
            return self.add_proxy(proxy_type, host, port, username, password)
            
        except Exception as e:
            logger.error(f"Failed to parse proxy string: {e}")
            return None

    def import_proxies_from_file(self, file_path: Path) -> int:
        """Import proxies from a file (one per line)."""
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxy = self.parse_proxy_string(line)
                    if proxy:
                        count += 1
        logger.info(f"Imported {count} proxies from {file_path}")
        return count
