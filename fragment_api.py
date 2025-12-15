"""
Fragment API 模块
直接调用 Fragment API 进行会员开通等操作
"""

import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class FragmentAPI:
    """Fragment API 客户端"""
    
    BASE_URL = "https://fragment.com"
    
    def __init__(self, hash_value: str, cookies: Optional[Dict[str, str]] = None):
        """
        初始化 Fragment API 客户端
        
        Args:
            hash_value: Fragment 认证 hash
            cookies: 可选的 cookies 字典
        """
        self.hash = hash_value
        self.cookies = cookies or {}
        self.session = requests.Session()
        
        # 设置默认 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://fragment.com',
            'Referer': 'https://fragment.com/premium',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
        })
        
        # 设置 cookies
        if self.cookies:
            for key, value in self.cookies.items():
                self.session.cookies.set(key, value)
    
    def call_api(self, method: str, **params) -> Dict:
        """
        调用 Fragment API
        
        Args:
            method: API 方法名
            **params: 其他参数
            
        Returns:
            dict: API 响应
        """
        try:
            logger.info(f"调用 Fragment API: method={method}, params={params}")
            
            response = self.session.post(
                f"{self.BASE_URL}/api",
                params={'hash': self.hash},
                data={'method': method, **params}
            )
            
            logger.debug(f"API Response Status: {response.status_code}")
            logger.debug(f"API Response Headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"API Response: {result}")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP 错误: {e}", exc_info=True)
            return {'ok': False, 'error': f'HTTP {response.status_code}: {str(e)}'}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {e}", exc_info=True)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"❌ API 调用失败: {e}", exc_info=True)
            return {'ok': False, 'error': str(e)}
    
    def update_premium_state(self, mode='new', months=12, recipient=None, dh=None):
        """
        开通/赠送 Telegram Premium
        
        Args:
            mode: 'new' 表示新开通
            months: 月数 (3, 6, 12)
            recipient: 接收者用户名（赠送时使用）
            dh: 页面状态参数（从页面获取）
            
        Returns:
            dict: API 响应
        """
        params = {
            'mode': mode,
            'iv': 'false',
        }
        
        if dh:
            params['dh'] = str(dh)
        
        if recipient:
            params['recipient'] = recipient
        
        if months:
            params['months'] = str(months)
        
        logger.info(f"尝试开通 Premium: recipient={recipient}, months={months}")
        
        result = self.call_api('updatePremiumState', **params)
        
        if result.get('ok'):
            logger.info(f"✅ Premium 开通成功: {months} 个月")
        else:
            logger.error(f"❌ Premium 开通失败: {result.get('error', 'Unknown error')}")
        
        return result
    
    def get_premium_info(self):
        """
        获取会员信息
        
        Returns:
            dict: API 响应
        """
        logger.info("获取 Premium 信息")
        return self.call_api('getPremiumInfo')
    
    def get_history(self):
        """
        获取交易历史
        
        Returns:
            dict: API 响应
        """
        logger.info("获取交易历史")
        return self.call_api('getHistory')
    
    def get_balance(self):
        """
        获取账户余额
        
        Returns:
            dict: API 响应
        """
        logger.info("获取账户余额")
        return self.call_api('getBalance')
    
    def gift_premium_by_user_id(self, user_id: int, months: int = 12, dh=None):
        """
        通过 User ID 赠送 Premium
        
        Args:
            user_id: Telegram User ID
            months: 月数 (3, 6, 12)
            dh: 页面状态参数
            
        Returns:
            dict: API 响应
        """
        params = {
            'mode': 'new',
            'iv': 'false',
            'user_id': str(user_id),
            'months': str(months),
        }
        
        if dh:
            params['dh'] = str(dh)
        
        logger.info(f"通过 User ID 赠送 Premium: user_id={user_id}, months={months}")
        
        result = self.call_api('giftPremium', **params)
        
        if result.get('ok'):
            logger.info(f"✅ Premium 赠送成功: user_id={user_id}, {months} 个月")
        else:
            logger.error(f"❌ Premium 赠送失败: {result.get('error', 'Unknown error')}")
        
        return result
