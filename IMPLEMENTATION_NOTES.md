# Implementation Notes: Telegram Premium Bot Improvements

This document describes the implementation of three major improvements to the Telegram Premium bot.

## Issue 1: Gift Recipient Username Resolution

### Problem
The bot could not reliably resolve @username to user_id for gift recipients, especially when users haven't interacted with the bot.

### Solution
Implemented a three-tier fallback system:

1. **Text Mention Entities** (Priority 1)
   - If user uses @ mention that creates a text_mention entity, extract user_id directly
   - Most reliable when available

2. **Bot API get_chat** (Priority 2)
   - Try `bot.get_chat(@username)` 
   - Works if user has interacted with bot or has open privacy settings

3. **Telethon Resolver** (Priority 3, New)
   - Falls back to Telethon client to resolve username
   - Can access users that Bot API cannot
   - Created `telethon_resolver.py` module

4. **Username-Only Fallback**
   - If all methods fail, allow proceeding with username only
   - Store `recipient_username` without `recipient_id`
   - Retry Telethon resolution during payment fulfillment

### Key Files
- `telethon_resolver.py` - New module for Telethon-based resolution
- `main.py:fetch_recipient_info()` - Updated with Telethon fallback
- `main.py:monitor_payment()` - Added Telethon retry for username-only orders
- `main.py:verify_payment()` - Added Telethon retry for username-only orders
- `main.py:fulfill_order_immediately()` - Added Telethon retry for username-only orders
- `.env.example` - Added Telethon configuration

### Configuration
New environment variables in `.env.example`:
```env
TELEGRAM_API_ID=2040  # Default public test API
TELEGRAM_API_HASH=b18441a1ff607e10a989891a5462e627
TELEGRAM_PHONE=  # International format, e.g., +8613800138000
TELEGRAM_SESSION=resolver_session
TELEGRAM_2FA_PASSWORD=  # Optional, if 2FA enabled
```

## Issue 2: Observability and Logging Improvements

### Problem
- Difficult to track bot activity and debug issues
- Message edit failures caused "no reaction" confusion

### Solution

#### Bot Identity Logging
- Added `post_init` callback in `main()` 
- Logs bot ID and username on startup using `getMe()`

#### Callback Query Logging
- Added INFO-level logging in `button_callback()`
- Logs: user_id, username, callback_data
- Format: `📱 Callback Query: user_id=123, username=john, data=buy_premium_3`

#### Safe Message Edit Helper
- Created `safe_edit_message()` function
- Automatically detects if message is photo+caption or text
- Uses `edit_caption` for photo messages, `edit_text` for text messages
- Falls back to sending new message if edit fails
- Prevents "no reaction" errors

### Key Files
- `main.py:main()` - Added post_init for bot identity logging
- `main.py:button_callback()` - Added INFO-level callback logging
- `main.py:safe_edit_message()` - New helper function
- `main.py:verify_payment()` - Updated to use safe_edit_message

## Issue 3: Balance-first Payment Strategy (B1)

### Problem
Users with account balance could not use it for purchases without manual intervention.

### Solution
Implemented B1 strategy: prioritize user balance, then on-chain payment.

#### Full Balance Coverage
When `user_balance >= price`:
1. Deduct balance immediately
2. Create order with `balance_to_use=price`, `remaining_amount=0`
3. Mark order as 'paid'
4. Fulfill immediately (gift Premium/Stars, mark as completed)
5. No on-chain payment needed

#### Partial Balance Coverage
When `0 < user_balance < price`:
1. Calculate: `balance_to_use=user_balance`, `remaining_amount=price-balance`
2. Create order with both values (balance NOT deducted yet)
3. Generate unique `remaining_amount` for chain payment
4. Show payment info for `remaining_amount`
5. After on-chain payment confirmed:
   - Deduct `balance_to_use` from user balance
   - Fulfill order

#### No Balance
When `user_balance == 0`:
1. Proceed as before with full on-chain payment
2. `balance_to_use=0`, `remaining_amount=price`

### Database Changes
Updated `create_order()` to accept:
- `balance_to_use`: Amount from user balance (default 0.0)
- `remaining_amount`: Amount to pay on-chain (default price)

### Key Files
- `main.py:create_order()` - Added balance_to_use and remaining_amount fields
- `main.py:fulfill_order_immediately()` - New helper for balance-paid orders
- `main.py:handle_self_purchase()` - Implemented B1 strategy
- `main.py:handle_gift_confirmation()` - Implemented B1 strategy
- `main.py:handle_stars_purchase()` - Implemented B1 strategy
- `main.py:monitor_payment()` - Deduct balance_to_use after chain payment
- `main.py:verify_payment()` - Deduct balance_to_use after chain payment
- `main.py:send_payment_info()` - Added balance_info parameter

### Order Fields
New fields in order documents:
```python
{
    'balance_to_use': 5.0,      # Amount from balance (deducted at payment)
    'remaining_amount': 3.1234  # Unique amount for chain payment
}
```

### Flow Example
User buys 12-month Premium ($15.00), has $5 balance:

1. Order created: `balance_to_use=$5.00`, `remaining_amount=$10.1234` (unique)
2. User pays $10.1234 on-chain
3. Chain payment detected
4. Balance deducted: $5.00
5. Total paid: $10.1234 + $5.00 = $15.1234 ≈ $15.00
6. Premium gifted

## Testing Recommendations

### Username Resolution
1. Test with user who has interacted with bot (should use Bot API)
2. Test with user who hasn't interacted (should try Telethon)
3. Test with @mention using autocomplete (should extract text_mention)
4. Test with invalid username (should offer username-only option)
5. Test username-only order fulfillment (should retry Telethon)

### Balance-first Payments
1. Test with balance > price (should deduct and fulfill immediately)
2. Test with 0 < balance < price (should use partial balance)
3. Test with balance = 0 (should proceed normally)
4. Test gift orders with all balance scenarios
5. Test stars orders with all balance scenarios
6. Verify balance deduction happens AFTER chain payment

### Observability
1. Check startup logs for bot identity
2. Monitor callback query logs during testing
3. Test message edits on photo-based payment messages
4. Verify fallback to new message if edit fails

## Migration Notes

### First-time Telethon Setup
1. Copy `.env.example` settings to `.env`
2. Set `TELEGRAM_PHONE` if you want to use Telethon resolver
3. First run will require phone verification code
4. Session saved to `resolver_session.session` file
5. Subsequent runs use saved session

### Existing Orders
- Existing orders don't have `balance_to_use` or `remaining_amount` fields
- Code handles this gracefully: defaults to 0.0 and price respectively
- No database migration required

## Security Considerations

1. **Balance Deduction Timing**: Balance is deducted atomically AFTER on-chain payment confirmation to prevent race conditions
2. **Unique Amounts**: `remaining_amount` uses `generate_unique_price()` to prevent payment confusion
3. **Telethon Session**: Session file should be protected, contains authentication
4. **2FA Password**: Store in environment variable, not in code

## Performance Impact

- Telethon resolution adds ~1-2 seconds for username-only recipients
- Balance checks are single database query (negligible)
- Full-balance orders complete immediately (faster than chain payment)

## Backward Compatibility

All changes are backward compatible:
- Existing orders without balance fields work normally
- Telethon resolver is optional (gracefully degrades if not configured)
- Message edit helper works with old-style edits
- All existing API calls remain unchanged
