#!/usr/bin/env python3
"""测试 Fragment 认证配置"""

import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from fragment_auth import FragmentAuth
from fragment_api import FragmentAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=" * 60)
    print("🧪 测试 Fragment 认证")
    print("=" * 60)
    
    # 加载认证数据
    auth = FragmentAuth('fragment_auth.json')
    if not auth.load_auth():
        print("\n❌ 认证数据加载失败")
        print("\n📝 请按以下步骤配置：")
        print("1. 复制 fragment_auth.json.example 为 fragment_auth.json")
        print("2. 在浏览器登录 https://fragment.com")
        print("3. 从开发者工具获取 hash 和 cookies")
        print("4. 填入 fragment_auth.json")
        return False
    
    print("✅ 认证数据加载成功\n")
    
    # 初始化 API
    auth_data = auth.get_auth_data()
    api = FragmentAPI(
        hash_value=auth_data['hash'],
        cookies=auth_data['cookies'],
        headers=auth_data.get('headers')
    )
    
    # 测试连接
    print("=" * 60)
    print("🔗 测试 Fragment 连接...")
    print("=" * 60)
    
    if api.test_connection():
        print("\n✅ 连接成功！")
        print("\n🎉 Fragment 认证配置正确，可以正常使用")
        return True
    else:
        print("\n❌ 连接失败")
        print("\n可能原因：")
        print("- 认证数据已过期，请重新获取")
        print("- 网络连接问题")
        print("- Fragment 服务暂时不可用")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
