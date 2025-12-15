# Fragment API 故障排查指南

## 问题描述

Fragment API 调用返回 "Invalid method" 和 "Access denied" 错误，导致无法自动开通 Premium。

## 错误日志示例

```
2025-12-15 08:16:40,708 - fragment_api - INFO - API Response: {'error': 'Invalid method'}
2025-12-15 08:16:40,722 - fragment_api - INFO - API Response: {'error': 'Access denied'}
2025-12-15 08:16:40,722 - fragment_premium - ERROR - ❌Premium 开通失败: Access denied
2025-12-15 08:16:43,767 - __main__ - ERROR - ❌Failed to gift Premium: Access denied
```

## 可能原因

### 1. 认证数据过期 (80% 可能性)

Fragment 认证数据（cookies 和 hash）会定期过期。需要重新从浏览器获取。

**检查方法：**
```bash
# 检查 fragment_auth.json 文件的修改时间
ls -lh fragment_auth.json

# 如果是几天或几周前的，很可能已过期
```

### 2. API 方法名错误 (15% 可能性)

当前代码使用的方法名可能已经改变：
- `giftPremium` → 可能应该是 `gift_premium`, `sendGift` 等
- `updatePremiumState` → 可能有其他方法名

### 3. 参数格式错误 (5% 可能性)

API 参数格式可能有变化，例如：
- `user_id` 应该是字符串还是数字
- 需要额外的必需参数

## 排查步骤

### 步骤 1: 运行测试脚本

```bash
python test_fragment_api.py
```

这个脚本会：
- 测试 Fragment 连接
- 尝试获取 Premium 信息
- 尝试获取交易历史
- 详细记录所有 API 请求和响应

输出会同时显示在终端和保存到 `fragment_api_test.log`。

### 步骤 2: 更新认证数据

如果测试显示认证失败，需要更新 `fragment_auth.json`：

#### 2.1 在浏览器中打开 Fragment

1. 访问 https://fragment.com
2. 使用你的 Telegram 账号登录
3. 确保登录成功

#### 2.2 获取认证数据

打开浏览器开发者工具（F12）：

**获取 Cookies:**

1. 进入 `Application` (Chrome) 或 `Storage` (Firefox) 标签
2. 展开 `Cookies` → `https://fragment.com`
3. 找到并复制以下 cookies 的值：
   - `stel_ssid`
   - `stel_token`
   - `stel_dt`

**获取 Hash:**

1. 进入 `Network` 标签
2. 刷新页面或点击任何按钮
3. 查找名为 `api` 的请求
4. 查看请求的 URL 或参数，找到 `hash` 参数的值

#### 2.3 更新配置文件

编辑 `fragment_auth.json`：

```json
{
  "hash": "从 Network 请求中获取的 hash 值",
  "cookies": {
    "stel_ssid": "从 Cookies 中获取的 stel_ssid 值",
    "stel_token": "从 Cookies 中获取的 stel_token 值",
    "stel_dt": "从 Cookies 中获取的 stel_dt 值"
  },
  "headers": {}
}
```

### 步骤 3: 手动抓包分析真实 API

如果认证数据更新后仍然失败，需要分析 Fragment 真实的 API 调用：

#### 3.1 在浏览器中手动赠送 Premium

1. 在 Fragment 网站手动执行赠送 Premium 操作
2. 在 Network 标签中观察 API 请求
3. 记录以下信息：
   - 请求 URL（完整路径）
   - 请求方法（POST/GET）
   - 请求参数（query parameters）
   - 请求数据（form data 或 JSON）
   - 请求头（headers）
   - 响应数据

#### 3.2 对比代码实现

将抓包得到的信息与代码中的实现对比：

**检查文件：**
- `fragment_api.py` → `call_api()` 方法
- `fragment_api.py` → `gift_premium_by_user_id()` 方法
- `fragment_api.py` → `update_premium_state()` 方法

**对比内容：**
- API 端点是否正确（当前：`/api`）
- 方法名是否正确（当前：`giftPremium`, `updatePremiumState`）
- 参数名和格式是否正确
- 是否缺少必需参数

### 步骤 4: 修改代码

根据抓包结果修改 `fragment_api.py`：

#### 示例：如果方法名错误

```python
# 修改前
result = self.call_api('giftPremium', **params)

# 修改后（假设真实方法名是 gift_premium）
result = self.call_api('gift_premium', **params)
```

#### 示例：如果需要额外参数

```python
# 修改前
params = {
    'mode': 'new',
    'iv': 'false',
    'user_id': str(user_id),
    'months': str(months),
}

# 修改后（假设需要额外的 token 参数）
params = {
    'mode': 'new',
    'iv': 'false',
    'user_id': str(user_id),
    'months': str(months),
    'token': 'some_token_value',  # 新增参数
}
```

### 步骤 5: 重新测试

修改后重新运行测试脚本：

```bash
python test_fragment_api.py
```

如果仍然失败，重复步骤 3-4，直到找到正确的 API 调用方式。

## 临时解决方案

在 API 修复之前，可以手动处理已支付的订单：

### 1. 查询已支付但未完成的订单

可以通过日志或数据库查询找到状态为 `paid` 但 Premium 未开通的订单。

### 2. 在 Fragment 网站手动开通

1. 访问 https://fragment.com/premium
2. 手动为相应用户赠送 Premium
3. 在数据库中更新订单状态为 `completed`

### 3. 通知用户

如果订单较多，可以考虑通知用户 Premium 已经开通。

## 增强的日志

代码已增强日志输出，包括：

- 详细的请求 URL、参数、数据
- 完整的请求和响应头
- 原始响应文本（前 500 字符）
- 特定的错误详情

这些日志将帮助快速定位问题。

## 常见问题

### Q1: 如何判断认证数据是否有效？

运行测试脚本，如果"测试 1: Fragment 连接测试"通过，说明认证基本有效。

### Q2: 更新认证数据多久会过期？

通常几天到几周，取决于 Fragment 的策略。建议定期更新。

### Q3: 可以使用多个账号吗？

可以，但需要为每个账号创建不同的配置文件。

### Q4: 如果所有方法都失败怎么办？

1. 确认 Fragment API 是否有重大变更
2. 考虑联系 Fragment 支持
3. 作为备选，可以考虑使用 Telegram Bot API 的 Premium 功能（如果有）

## 相关文件

- `fragment_api.py` - Fragment API 客户端
- `fragment_premium.py` - Premium 管理器
- `fragment_auth.json` - 认证配置文件
- `test_fragment_api.py` - API 测试工具
- `fragment_api_test.log` - 测试日志输出

## 注意事项

⚠️ **安全提示：**
- 不要将 `fragment_auth.json` 提交到 Git
- 认证数据包含敏感信息，需要妥善保管
- 定期更换认证数据以提高安全性

⚠️ **测试提示：**
- 测试时使用小额度（3个月）Premium
- 确保测试的 User ID 正确
- 建议先在测试账号上验证

## 更新日志

- 2025-12-15: 添加详细的 API 调试日志
- 2025-12-15: 创建 test_fragment_api.py 测试工具
- 2025-12-15: 创建此故障排查指南
