# Username-Only Gifting Flow Implementation

## Overview

This document describes the implementation of the username-only gifting flow for Fragment Premium, aligning the bot with the exact browser network sequence.

## Key Changes

### 1. Username-Only Requirement

The gifting flow now **only supports @username** as the recipient identifier. User IDs without public usernames are no longer supported.

#### Why Username-Only?

- **Fragment API Requirement**: The browser's successful gifting flow uses the username in the gift page URL to establish context
- **Reliability**: Username-based gifting aligns with how Fragment's web interface works
- **Consistency**: Ensures the bot replicates the exact browser behavior

### 2. Browser-Exact Request Sequence

The new implementation replicates the exact browser request sequence:

#### Step A: Build Gifting Context
```
GET https://fragment.com/premium/gift?recipient=<username>&months=<months>
```
- Opens the gift page to establish context
- The page may redirect and include a recipient token in the final URL
- Extracts the `dh` parameter from the page HTML

#### Step B: Execute Gift API Call
```
POST https://fragment.com/api?hash=<hash>
Headers:
  - Referer: <final_gift_page_url_with_token>
  - (other standard headers)
  
Form Data:
  - mode=new
  - iv=false
  - dh=<extracted_value>
  - method=updatePremiumState
```

**Important Notes:**
- The payload is minimal - only `mode`, `iv`, `dh`, and `method`
- No `user_id`, `recipient`, or `months` in the form data
- The recipient context comes from the Referer header
- The months are part of the gift page URL, not the API payload

### 3. Input Validation Flow

When a user wants to gift Premium:

1. **@username Input** (Recommended):
   - User enters `@username`
   - Bot validates the username exists using Telethon
   - Proceeds to confirmation

2. **Numeric ID Input** (Converted or Rejected):
   - User enters a numeric ID (e.g., `123456789`)
   - Bot attempts to resolve the ID to a username using Telethon
   - If username exists: proceeds with the username
   - If no username: rejects and instructs user to set a public username

3. **Text Mention** (Supported):
   - User uses Telegram's @ mention feature
   - Bot extracts the username from the mention entity
   - Validates and proceeds

### 4. Order Data Structure

Orders now store:
```python
{
    'recipient_id': <user_id>,        # Optional, for display
    'recipient_username': <username>,  # Required for gifting
    # ... other fields
}
```

### 5. Fulfillment Flow

The fulfillment sequence ensures reliability:

1. **Payment Verification**: Verify USDT transaction on-chain
2. **Balance Deduction**: If order uses partial balance, deduct it now
3. **Username Resolution**: Ensure we have a valid username
4. **Gift Premium**: Call `fragment.gift_premium(username, months)`
5. **Mark Complete**: Update order status to 'completed'

**Critical**: Balance deduction happens BEFORE gifting to ensure funds are secured before attempting the gift operation.

## Code Changes

### fragment_api.py

Added new method `gift_premium_by_username()`:
```python
def gift_premium_by_username(self, username: str, months: int = 12):
    """
    Gift Premium using browser-exact request sequence
    
    Workflow:
    1. GET gift page: /premium/gift?recipient=<username>&months=<months>
    2. Extract dh parameter from page HTML
    3. POST to /api with minimal payload and gift page Referer
    """
    # ... implementation
```

### fragment_premium.py

Updated `gift_premium()` to accept username:
```python
def gift_premium(self, username: str, months: int = 12):
    """Gift Premium using username-only"""
    clean_username = username.lstrip('@')
    return self.api.gift_premium_by_username(clean_username, months)
```

### main.py

#### FragmentManager.gift_premium()
Changed signature from `(user_id, months)` to `(username, months)`

#### handle_gift_purchase_start()
Updated message to clarify username-only requirement

#### handle_text_message() - awaiting_recipient state
- Added numeric ID to username resolution using Telethon
- Rejects IDs without public usernames
- Enhanced error messages

#### Order Fulfillment Functions
Updated all three fulfillment functions:
- `fulfill_order_immediately()`
- `verify_payment()` monitor callback
- `monitor_payment()` background job

All now:
1. Ensure `recipient_username` is available
2. Attempt to resolve username if missing
3. Call `gift_premium(username, months)` instead of `gift_premium(user_id, months)`
4. Error gracefully if no username available

## Testing

### Test Script Updates

`test_fragment_api.py` now uses username:
```python
# Old:
test_gift_premium(premium, user_id=123456789, months=3)

# New:
test_gift_premium(premium, username="johndoe", months=3)
```

### Manual Testing Checklist

- [ ] Test with valid @username
- [ ] Test with username without @ prefix
- [ ] Test with numeric ID that has public username (should convert)
- [ ] Test with numeric ID without public username (should reject)
- [ ] Test with text mention entity
- [ ] Verify balance deduction happens before gifting
- [ ] Verify error handling when username not found
- [ ] Verify Fragment API receives correct request format

## Migration Guide

### For Existing Orders

Old orders may have `recipient_id` without `recipient_username`. The fulfillment code handles this:

1. If `recipient_username` exists: use it directly
2. If only `recipient_id` exists: attempt to resolve to username
3. If resolution fails: mark order as paid with error, notify user

### For API Consumers

If you have external code calling Fragment Premium functions:

```python
# Old API:
fragment.gift_premium(user_id=123456789, months=12)

# New API:
fragment.gift_premium(username="johndoe", months=12)
# or
fragment.gift_premium(username="@johndoe", months=12)  # @ is auto-stripped
```

## Security Considerations

1. **Username Validation**: Always validate usernames before attempting to gift
2. **Balance Security**: Balance is deducted AFTER on-chain payment but BEFORE gifting
3. **Error Tracking**: Failed gift attempts are tracked with `retry_count` and `last_error`
4. **Order Status**: Orders remain in 'paid' state (not 'failed') if gifting fails, allowing manual retry

## Error Handling

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "No username available" | User has no public username | User must set a public username in Telegram settings |
| "Telethon resolver not available" | Telethon sessions not configured | Configure Telethon sessions in `sessions/` directory |
| "Cannot gift Premium without username" | Order has no username and ID resolution failed | Manual intervention required |
| Fragment API errors | Auth expired or network issues | Check `fragment_auth.json` and connectivity |

## Future Enhancements

Potential improvements for consideration:

1. **Username Caching**: Cache user_id to username mappings to reduce Telethon calls
2. **Batch Gifting**: Support gifting to multiple recipients
3. **Username Change Detection**: Handle cases where recipient changes their username
4. **Retry with Backoff**: Implement exponential backoff for failed gift attempts

## References

- Fragment Premium Gift Page: `https://fragment.com/premium/gift`
- Problem Statement: See task description for browser DevTools evidence
- Telethon Documentation: For username resolution APIs

## Change Log

- 2025-12-15: Initial implementation of username-only gifting flow
- 2025-12-15: Added browser-exact request sequence
- 2025-12-15: Updated all fulfillment paths to use username
