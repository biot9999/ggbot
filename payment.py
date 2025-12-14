import aiohttp
import asyncio
import logging
from typing import Optional, Dict
import config
import traceback

logger = logging.getLogger(__name__)

class TronPayment:
    def __init__(self):
        self.api_url = config.TRONGRID_API_URL
        self.api_key = config.TRONGRID_API_KEY
        self.usdt_contract = config.USDT_TRC20_CONTRACT
        self.wallet_address = config.PAYMENT_WALLET_ADDRESS
        self.use_free_api = False  # Flag to track if we're using free API
        self.retry_count = 0
        self.max_retries = 3
    
    def _get_headers(self, use_api_key=True):
        """Get headers for TronGrid API"""
        headers = {'Content-Type': 'application/json'}
        if use_api_key and self.api_key and not self.use_free_api:
            headers['TRON-PRO-API-KEY'] = self.api_key
        return headers
    
    def _should_fallback_to_free_api(self, status_code: int) -> bool:
        """Check if we should fallback to free API based on error code"""
        return status_code in [401, 403]
    
    async def get_account_transactions(self, address: str, limit: int = 20) -> Optional[list]:
        """Get TRC20 transactions for an address with automatic fallback to free API"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.api_url}/v1/accounts/{address}/transactions/trc20"
                params = {
                    'limit': limit,
                    'contract_address': self.usdt_contract
                }
                
                headers = self._get_headers(use_api_key=True)
                
                logger.debug(f"TronGrid API Request - URL: {url}")
                logger.debug(f"TronGrid API Request - Params: {params}")
                logger.debug(f"TronGrid API Request - Headers: {headers}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, headers=headers) as response:
                        response_text = await response.text()
                        logger.debug(f"TronGrid API Response - Status: {response.status}")
                        logger.debug(f"TronGrid API Response - Body: {response_text}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"Successfully fetched {len(data.get('data', []))} transactions")
                                return data.get('data', [])
                            except Exception as e:
                                logger.error(f"Error parsing response JSON: {e}")
                                return None
                                
                        elif self._should_fallback_to_free_api(response.status):
                            if not self.use_free_api:
                                logger.warning(
                                    f"TronGrid API {response.status} - Falling back to free public API. "
                                    f"Free API has rate limits: 5 requests/second, 10,000 requests/day"
                                )
                                self.use_free_api = True
                                # Retry with free API
                                continue
                            else:
                                logger.error(
                                    f"TronGrid Free API also returned {response.status}. "
                                    f"You may have exceeded rate limits."
                                )
                                # Wait before retry
                                await asyncio.sleep(2 ** attempt)
                                continue
                                
                        elif response.status == 429:
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"TronGrid API 429 Too Many Requests - Rate limit exceeded. "
                                f"Waiting {wait_time}s before retry {attempt+1}/{self.max_retries}"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Failed to get transactions: HTTP {response.status} - {response_text}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error getting transactions (attempt {attempt+1}/{self.max_retries}): {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    async def verify_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Verify a specific transaction with retry logic"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.api_url}/v1/transactions/{tx_hash}/info"
                headers = self._get_headers(use_api_key=True)
                
                logger.debug(f"TronGrid Verify TX Request - URL: {url}")
                logger.debug(f"TronGrid Verify TX Request - Headers: {headers}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        logger.debug(f"TronGrid Verify TX Response - Status: {response.status}")
                        logger.debug(f"TronGrid Verify TX Response - Body: {response_text}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"Transaction {tx_hash[:8]}... verified successfully")
                                return data
                            except Exception as e:
                                logger.error(f"Error parsing transaction response: {e}")
                                return None
                                
                        elif self._should_fallback_to_free_api(response.status):
                            if not self.use_free_api:
                                logger.warning(f"Falling back to free API for transaction verification")
                                self.use_free_api = True
                                continue
                            else:
                                logger.error(f"Free API also failed with status {response.status}")
                                await asyncio.sleep(2 ** attempt)
                                continue
                        else:
                            logger.error(f"Failed to verify transaction: HTTP {response.status} - {response_text}")
                            return None
                            
            except Exception as e:
                logger.error(f"Error verifying transaction (attempt {attempt+1}/{self.max_retries}): {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    async def check_payment(self, amount: float, timeout: int = 1800) -> Optional[Dict]:
        """
        Monitor for incoming payment of specified amount
        Returns transaction details if payment found within timeout
        """
        import time
        start_time = time.time()
        last_checked_timestamp = start_time * 1000  # Convert to milliseconds
        
        logger.info(f"Starting payment monitoring for amount: ${amount:.4f}")
        logger.debug(f"Monitor timeout: {timeout}s, check interval: {config.PAYMENT_CHECK_INTERVAL}s")
        
        while (time.time() - start_time) < timeout:
            try:
                logger.debug(f"Checking for payment... (elapsed: {int(time.time() - start_time)}s)")
                transactions = await self.get_account_transactions(self.wallet_address)
                
                if transactions:
                    logger.debug(f"Found {len(transactions)} recent transactions")
                    for tx in transactions:
                        tx_timestamp = tx.get('block_timestamp', 0)
                        
                        # Only check transactions after we started monitoring
                        if tx_timestamp < last_checked_timestamp:
                            continue
                        
                        # Check if transaction is to our wallet
                        if tx.get('to') != self.wallet_address:
                            logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... not to our wallet")
                            continue
                        
                        # Check if transaction is USDT TRC20
                        if tx.get('token_info', {}).get('address') != self.usdt_contract:
                            logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... not USDT")
                            continue
                        
                        # Check amount (convert from smallest unit)
                        tx_amount = float(tx.get('value', 0)) / (10 ** tx.get('token_info', {}).get('decimals', 6))
                        
                        logger.debug(f"TX {tx.get('transaction_id', '')[:8]}... amount: ${tx_amount:.4f} (expected: ${amount:.4f})")
                        
                        # Use tight tolerance for unique amounts (0.00001 = 1/100 of smallest increment)
                        if abs(tx_amount - amount) < 0.00001:
                            logger.info(f"✅ Payment found! TX: {tx.get('transaction_id')}, Amount: ${tx_amount:.4f}")
                            return {
                                'tx_hash': tx.get('transaction_id'),
                                'amount': tx_amount,
                                'from': tx.get('from'),
                                'to': tx.get('to'),
                                'timestamp': tx_timestamp
                            }
                
                # Wait before next check
                await asyncio.sleep(config.PAYMENT_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error checking payment: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(config.PAYMENT_CHECK_INTERVAL)
        
        logger.warning(f"Payment monitoring timeout after {timeout}s")
        return None
    
    async def verify_usdt_authenticity(self, tx_hash: str) -> bool:
        """
        Verify that the USDT transaction is real (not fake USDT)
        Checks if the token contract matches the official USDT TRC20 contract
        """
        try:
            logger.debug(f"Verifying USDT authenticity for TX: {tx_hash}")
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                logger.warning(f"Could not fetch transaction info for {tx_hash}")
                return False
            
            # Extract contract address from transaction
            trc20_transfers = tx_info.get('trc20_transfer', [])
            if not trc20_transfers:
                logger.warning(f"No TRC20 transfers found in transaction {tx_hash}")
                return False
            
            contract_address = trc20_transfers[0].get('token_address', '')
            
            logger.debug(f"Transaction contract: {contract_address}, Official USDT: {self.usdt_contract}")
            
            # Verify it's the official USDT contract
            if contract_address.upper() != self.usdt_contract.upper():
                logger.warning(f"⚠️ Fake USDT detected! TX: {tx_hash}, Contract: {contract_address}")
                return False
            
            logger.info(f"✅ Authentic USDT verified for TX: {tx_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying USDT authenticity: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def get_transaction_details(self, tx_hash: str) -> Optional[Dict]:
        """Get detailed information about a transaction"""
        try:
            logger.debug(f"Fetching transaction details for: {tx_hash}")
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                logger.warning(f"No transaction info returned for {tx_hash}")
                return None
            
            # Extract relevant information
            trc20_transfers = tx_info.get('trc20_transfer', [])
            if not trc20_transfers:
                logger.warning(f"No TRC20 transfers in transaction {tx_hash}")
                return None
            
            transfer = trc20_transfers[0]
            
            details = {
                'tx_hash': tx_hash,
                'from': transfer.get('from_address', ''),
                'to': transfer.get('to_address', ''),
                'amount': float(transfer.get('amount_str', 0)) / 1000000,  # USDT has 6 decimals
                'token_address': transfer.get('token_address', ''),
                'timestamp': tx_info.get('block_timestamp', 0),
                'confirmed': tx_info.get('ret', [{}])[0].get('contractRet') == 'SUCCESS'
            }
            
            logger.debug(f"Transaction details: {details}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

# Global payment instance
tron_payment = TronPayment()
