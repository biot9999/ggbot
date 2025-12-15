# Username-Only Gifting Flow - Quick Reference

## Before vs After Comparison

### Input Acceptance

| Input Type | Before | After |
|------------|--------|-------|
| @username | ✅ Accepted | ✅ Accepted |
| User ID (numeric) | ✅ Accepted | ⚠️ Converted to username or rejected |
| Text mention | ✅ Accepted | ✅ Accepted (username extracted) |

### Gifting API Calls

#### Before (User ID Based)
```python
# Method 1: gift_premium_by_user_id
POST /api?hash=X
Form: mode=new, iv=false, user_id=123456789, months=12, method=giftPremium

# Method 2: update_premium_state
POST /api?hash=X
Form: mode=new, iv=false, recipient=123456789, months=12, method=updatePremiumState
```

#### After (Username Based - Browser Exact)
```python
# Step 1: Get gift page context
GET /premium/gift?recipient=johndoe&months=12

# Step 2: Extract dh from page HTML
dh = "1450965014"  # Extracted from page

# Step 3: Call API with minimal payload
POST /api?hash=X
Headers: Referer: https://fragment.com/premium/gift?recipient=...
Form: mode=new, iv=false, dh=1450965014, method=updatePremiumState
```

**Key Difference:** Recipient context comes from Referer URL, not form data!

## User Flow Examples

### Example 1: Valid Username
```
User inputs: @johndoe
  ↓
Bot validates username via Telethon
  ↓
Show confirmation with user profile
  ↓
User confirms and pays
  ↓
Bot calls fragment.gift_premium("johndoe", 12)
  ↓
Success! ✅
```

### Example 2: Numeric ID with Public Username
```
User inputs: 123456789
  ↓
Bot resolves ID → @johndoe via Telethon
  ↓
Show confirmation: "Will gift to @johndoe"
  ↓
User confirms and pays
  ↓
Bot calls fragment.gift_premium("johndoe", 12)
  ↓
Success! ✅
```

### Example 3: Numeric ID without Public Username
```
User inputs: 987654321
  ↓
Bot attempts resolution via Telethon
  ↓
User has no public username ❌
  ↓
Bot rejects with error message:
"该用户没有设置公开的 username
请让对方在 Settings → Edit Profile → Username 设置"
  ↓
User must get recipient to set username
```

### Example 4: Numeric ID Not in Telethon Cache
```
User inputs: 5611529170
  ↓
Bot attempts resolution via Telethon
  ↓
User not found in session cache ❌
(Telethon limitation: can only resolve IDs seen before)
  ↓
Bot rejects with error message:
"无法通过 User ID 查找用户
系统无法访问该用户的信息（用户可能未与 Bot 互动过）
请直接使用对方的 @username 进行赠送"
  ↓
User must provide @username instead
```

**⚠️ Telethon Limitation Explained:**

Telethon can only resolve user IDs that it has previously encountered in chats/channels accessible to its sessions. This is a Telegram API limitation - not a bug. The bot cannot look up arbitrary user IDs without prior interaction. This is why @username is the recommended and most reliable input method.

## Payment & Fulfillment Sequence

### Balance-First Strategy (Preserved)

```
1. User confirms purchase
   ↓
2. Check user balance
   ↓
   ┌─────────────────┬─────────────────┬─────────────────┐
   │ Full Balance    │ Partial Balance │ No Balance      │
   ├─────────────────┼─────────────────┼─────────────────┤
   │ Deduct balance  │ Show payment    │ Show payment    │
   │ Mark paid       │ info            │ info            │
   │ Gift Premium ✓  │ ↓               │ ↓               │
   │                 │ Wait for chain  │ Wait for chain  │
   │                 │ ↓               │ ↓               │
   │                 │ Verify TX       │ Verify TX       │
   │                 │ ↓               │ ↓               │
   │                 │ Deduct balance  │ Mark paid       │
   │                 │ ↓               │ ↓               │
   │                 │ Mark paid       │ Gift Premium ✓  │
   │                 │ ↓               │                 │
   │                 │ Gift Premium ✓  │                 │
   └─────────────────┴─────────────────┴─────────────────┘
```

**Critical:** Balance deduction ALWAYS happens before gifting!

## Error Handling

| Scenario | Action | Order Status |
|----------|--------|--------------|
| No username available | Attempt ID→username resolution | `paid` (with error) |
| Username resolution fails | Notify user, don't gift | `paid` (with error) |
| Fragment API error | Keep for retry | `paid` (with error) |
| Gift successful | Complete order | `completed` |

## Code Flow Reference

### 1. Input Handling
`main.py:handle_text_message()` → awaiting_recipient state
- Lines ~3318-3520: Input parsing & validation
- Uses Telethon for ID → username resolution

### 2. Order Creation
`main.py:handle_gift_confirmation()`
- Lines ~2905-2957: Create order with recipient_username

### 3. Order Fulfillment
Three paths (all use username now):

**Path A: Immediate (full balance)**
`main.py:fulfill_order_immediately()`
- Lines 2516-2610

**Path B: On-chain payment verification**
`main.py:verify_payment()`
- Lines 3641-3654: Balance deduction
- Line 3712: Gift Premium with username

**Path C: Background monitor**
`main.py:monitor_payment()`
- Similar flow to Path B

### 4. Fragment API
`fragment_api.py:gift_premium_by_username()`
- Lines 273-391: Browser-exact implementation

## Testing Commands

```bash
# Syntax check
python3 -m py_compile fragment_api.py fragment_premium.py main.py

# Run test script (requires fragment_auth.json)
python3 test_fragment_api.py

# Check function signatures
grep -n "def gift_premium" fragment_api.py fragment_premium.py main.py
```

## Common Issues & Solutions

### Issue: "No username available for recipient"
**Cause:** User has no public username set  
**Solution:** User must set username in Telegram Settings

### Issue: "Telethon resolver not available"
**Cause:** No session files in sessions/ directory  
**Solution:** Configure at least one Telethon session

### Issue: Fragment API returns error
**Cause:** Auth tokens expired  
**Solution:** Update fragment_auth.json with fresh cookies and hash

### Issue: Gift succeeds but order shows "paid"
**Cause:** Network issue during status update  
**Solution:** Check logs, manually verify gift, update order status

## Important Notes

1. **Username is Required**: Cannot gift without a public username
2. **Referer is Critical**: Fragment API uses Referer to determine recipient
3. **Balance Security**: Balance deducted before gifting attempt
4. **Retry Safety**: Failed gifts keep order in "paid" status for manual retry
5. **Case Sensitivity**: Usernames are case-insensitive in Telegram

## Migration from Old Code

If you have code calling the old API:

```python
# ❌ Old (no longer works)
fragment.gift_premium(user_id=123456789, months=12)

# ✅ New (required)
fragment.gift_premium(username="johndoe", months=12)
# or with @ prefix (auto-stripped)
fragment.gift_premium(username="@johndoe", months=12)
```

## See Also

- `USERNAME_GIFTING_IMPLEMENTATION.md` - Detailed technical documentation
- `fragment_auth.json.example` - Example auth configuration
- `FRAGMENT_API_DEBUG.md` - Troubleshooting guide
