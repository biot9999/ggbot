"""
Fragment 认证模块
从配置文件加载手动获取的认证数据，避免账号冻结风险
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class FragmentAuth:
    """Fragment 认证管理器 - 使用手动认证方式"""
    
    def __init__(self, config_file: str = 'fragment_auth.json'):
        """
        初始化 Fragment 认证管理器
        
        Args:
            config_file: 认证配置文件路径（JSON格式）
        """
        self.config_file = config_file
        self.hash = None
        self.cookies = {}
        self.headers = {}
        self._loaded = False
    
    def load_auth(self) -> bool:
        """
        从配置文件加载认证数据
        
        Returns:
            bool: 加载是否成功
        """
        try:
            config_path = Path(self.config_file)
            
            if not config_path.exists():
                logger.error(f"❌ 认证文件不存在: {self.config_file}")
                logger.error("📝 请按以下步骤配置：")
                logger.error("1. 复制 fragment_auth.json.example 为 fragment_auth.json")
                logger.error("2. 在浏览器登录 https://fragment.com")
                logger.error("3. 从开发者工具获取 hash 和 cookies")
                logger.error("4. 填入 fragment_auth.json")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证必需字段
            if 'hash' not in config:
                logger.error("❌ 配置文件缺少 'hash' 字段")
                return False
            
            if 'cookies' not in config:
                logger.error("❌ 配置文件缺少 'cookies' 字段")
                return False
            
            # 加载认证数据
            self.hash = config['hash']
            self.cookies = config['cookies']
            self.headers = config.get('headers', {})
            
            # 验证关键 cookies
            required_cookies = ['stel_ssid']
            missing_cookies = [c for c in required_cookies if c not in self.cookies]
            
            if missing_cookies:
                logger.warning(f"⚠️ 缺少关键 cookies: {', '.join(missing_cookies)}")
                logger.warning("认证可能会失败，请确保从浏览器获取完整的 cookies")
            
            self._loaded = True
            logger.info("✅ Fragment 认证数据加载成功")
            logger.debug(f"Hash: {self.hash[:16]}..." if self.hash else "Hash: None")
            logger.debug(f"Cookies: {list(self.cookies.keys())}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 配置文件格式错误: {e}", exc_info=True)
            logger.error("请检查 JSON 格式是否正确")
            return False
        except Exception as e:
            logger.error(f"❌ 加载认证数据失败: {e}", exc_info=True)
            return False
    
    def get_auth_data(self) -> Optional[Dict]:
        """
        获取认证数据
        
        Returns:
            dict: 包含 hash, cookies, headers 的字典，未加载返回 None
        """
        if not self._loaded:
            logger.error("❌ 认证数据未加载，请先调用 load_auth()")
            return None
        
        return {
            'hash': self.hash,
            'cookies': self.cookies,
            'headers': self.headers
        }
    
    def is_loaded(self) -> bool:
        """
        检查认证数据是否已加载
        
        Returns:
            bool: 是否已加载
        """
        return self._loaded
