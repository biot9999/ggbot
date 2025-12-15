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
    API_TIMEOUT = 30  # API 请求超时时间（秒）
    
    def __init__(self, hash_value: str, cookies: Optional[Dict[str, str]] = None, 
                 headers: Optional[Dict[str, str]] = None):
        """
        初始化 Fragment API 客户端
        
        Args:
            hash_value: Fragment 认证 hash
            cookies: 可选的 cookies 字典
            headers: 可选的自定义 headers
        """
        self.hash = hash_value
        self.cookies = cookies or {}
        self.session = requests.Session()
        
        # 设置默认 headers
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://fragment.com',
            'Referer': 'https://fragment.com/premium',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        # 合并自定义 headers
        if headers:
            default_headers.update(headers)
        
        self.session.headers.update(default_headers)
        
        # 设置 cookies
        if self.cookies:
            for key, value in self.cookies.items():
                self.session.cookies.set(key, value, domain='fragment.com')
    
    def test_connection(self) -> bool:
        """
        测试 Fragment 连接和认证是否有效
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info("测试 Fragment 连接...")
            
            response = self.session.get(
                f"{self.BASE_URL}/",
                timeout=self.API_TIMEOUT,
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            # 检查是否成功访问
            if response.status_code == 200:
                logger.info("✅ Fragment 连接测试成功")
                logger.debug(f"响应长度: {len(response.text)} 字节")
                return True
            else:
                logger.warning(f"⚠️ Fragment 连接返回非 200 状态码: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Fragment 连接超时（{self.API_TIMEOUT}秒）")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Fragment 连接失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Fragment 连接测试失败: {e}", exc_info=True)
            return False
    
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
            
            # Build request data
            request_data = {'method': method, **params}
            request_url = f"{self.BASE_URL}/api"
            request_params = {'hash': self.hash}
            
            # Log detailed request information
            logger.debug(f"Request URL: {request_url}")
            logger.debug(f"Request params: {request_params}")
            logger.debug(f"Request data: {request_data}")
            logger.debug(f"Request headers: {dict(self.session.headers)}")
            logger.debug(f"Request cookies: {dict(self.session.cookies)}")
            
            response = self.session.post(
                request_url,
                params=request_params,
                data=request_data,
                timeout=self.API_TIMEOUT
            )
            
            logger.debug(f"API Response Status: {response.status_code}")
            logger.debug(f"API Response Headers: {dict(response.headers)}")
            
            # Log raw response text for debugging (first 500 chars, be careful with sensitive data)
            try:
                response_text = response.text
                # Sanitize potential sensitive data from logs
                sanitized_text = response_text[:500]
                # Don't log if it looks like it contains tokens or sensitive cookies
                if 'token' not in sanitized_text.lower() and 'password' not in sanitized_text.lower():
                    logger.debug(f"API Response Text (first 500 chars): {sanitized_text}")
                else:
                    logger.debug("API Response Text: [Contains sensitive data, not logged]")
            except Exception as e:
                logger.warning(f"Could not log response text: {e}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"API Response: {result}")
            
            # Log specific error details if present
            if not result.get('ok', True) and result.get('error'):
                logger.error(f"❌ API Error Details: {result['error']}")
                if 'error_description' in result:
                    logger.error(f"   Description: {result['error_description']}")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ API 请求超时（{self.API_TIMEOUT}秒）")
            return {'ok': False, 'error': f'Request timeout after {self.API_TIMEOUT}s'}
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code if 'response' in locals() else 'unknown'
            logger.error(f"❌ HTTP 错误 {status_code}: {e}", exc_info=True)
            # Try to parse error response
            try:
                if 'response' in locals():
                    error_data = response.json()
                    logger.error(f"   Error response data: {error_data}")
            except:
                pass
            return {'ok': False, 'error': f'HTTP {status_code}: {str(e)}'}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ 网络连接失败: {e}", exc_info=True)
            return {'ok': False, 'error': f'Connection error: {str(e)}'}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求失败: {e}", exc_info=True)
            return {'ok': False, 'error': str(e)}
        except ValueError as e:
            logger.error(f"❌ JSON 解析失败: {e}", exc_info=True)
            if 'response' in locals():
                logger.error(f"   Response text: {response.text[:500]}")
            return {'ok': False, 'error': f'Invalid JSON response: {str(e)}'}
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
