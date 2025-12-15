# 快速开始指南

## 📋 前置要求

- Python 3.8 或更高版本
- MongoDB 数据库
- TRC20 钱包地址
- Telegram Bot Token

## ⚡ 5分钟快速部署

### 1. 获取 Telegram Bot Token
1. 在 Telegram 搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建机器人
3. 按提示设置名称，获得 Token

### 2. 获取管理员 ID
1. 在 Telegram 搜索 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息，复制你的 ID

### 3. 准备 TRC20 钱包
1. 安装 TronLink 或其他支持 TRC20 的钱包
2. 复制你的钱包地址

### 4. 配置机器人

```bash
# 克隆项目
git clone https://github.com/biot9999/ggbot.git
cd ggbot

# 复制配置文件
cp .env.example .env

# 编辑配置文件
nano .env
```

最少需要配置以下内容：
```env
TELEGRAM_BOT_TOKEN=你的机器人Token
ADMIN_USER_IDS=你的用户ID
PAYMENT_WALLET_ADDRESS=你的TRC20钱包地址

# Telegram API 配置（用于 Fragment 认证）
TELEGRAM_API_ID=2040
TELEGRAM_API_HASH=b18441a1ff607e10a989891a5462e627
TELEGRAM_PHONE=+你的手机号（国际格式）
```

### 5. 启动机器人

```bash
# 使用启动脚本（推荐）
chmod +x start.sh
./start.sh

# 或手动启动
pip install -r requirements.txt
python main.py
```

### 6. 配置 Fragment 认证

1. 在 Telegram 中向机器人发送 `/start`
2. 发送 `/login` 开始 Telegram 登录流程
3. 按提示输入验证码（从 Telegram 接收）
4. 登录成功后 session 自动保存，无需重复登录

## 🎯 测试机器人

1. 在 Telegram 中找到你的机器人
2. 发送 `/start` 查看欢迎消息
3. 发送 `/buy` 测试购买流程
4. 发送 `/admin` 查看管理面板（仅管理员）

## 💡 常见问题

### Q: 机器人没有响应？
A: 检查 Token 是否正确，MongoDB 是否运行

### Q: 如何修改价格？
A: 使用 `/setprice 3 5.99` 命令（管理员）

### Q: Fragment 登录失败？
A: 检查 .env 中的 TELEGRAM_PHONE 配置是否正确（国际格式）

### Q: 支付检测不到？
A: 确认钱包地址正确，用户使用 TRC20 网络

## 🔧 高级配置

### TronGrid API Key（可选，但推荐）
1. 访问 https://www.trongrid.io
2. 注册并创建 API Key
3. 添加到 .env：`TRONGRID_API_KEY=your_key`

### 自定义价格
编辑 .env 文件：
```env
PRICE_3_MONTHS=5.00
PRICE_6_MONTHS=9.00
PRICE_12_MONTHS=15.00
```

### 生产环境部署
使用 systemd 服务：
```bash
# 编辑服务文件中的路径
sudo nano telegram-premium-bot.service

# 安装服务
sudo cp telegram-premium-bot.service /etc/systemd/system/
sudo systemctl enable telegram-premium-bot
sudo systemctl start telegram-premium-bot

# 查看状态
sudo systemctl status telegram-premium-bot
```

## 📱 用户使用流程

1. 用户发送 `/buy` 选择套餐
2. 机器人显示二维码和收款地址
3. 用户使用 USDT (TRC20) 支付
4. 用户点击"我已支付"按钮
5. 系统自动验证并开通会员

## 🛡️ 安全提示

- ✅ 不要泄露 Bot Token
- ✅ 妥善保管 .env 文件
- ✅ 定期备份数据库
- ✅ 使用 HTTPS 代理（生产环境）
- ✅ 设置防火墙规则

## 📞 获取帮助

如有问题，请：
1. 查看 README.md 详细文档
2. 检查故障排除部分
3. 在 GitHub 提交 Issue

---

祝您使用愉快！🎉
