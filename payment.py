import aiohttp
import asyncio
import logging
from typing import Optional, Dict
import config

logger = logging.getLogger(__name__)

class TronPayment:
    def __init__(self):
        self.api_url = config.TRONGRID_API_URL
        self.api_key = config.TRONGRID_API_KEY
        self.usdt_contract = config.USDT_TRC20_CONTRACT
        self.wallet_address = config.PAYMENT_WALLET_ADDRESS
    
    def _get_headers(self):
        """Get headers for TronGrid API"""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['TRON-PRO-API-KEY'] = self.api_key
        return headers
    
    async def get_account_transactions(self, address: str, limit: int = 20) -> Optional[list]:
        """Get TRC20 transactions for an address"""
        try:
            url = f"{self.api_url}/v1/accounts/{address}/transactions/trc20"
            params = {
                'limit': limit,
                'contract_address': self.usdt_contract
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self._get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        logger.error(f"Failed to get transactions: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return None
    
    async def verify_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Verify a specific transaction"""
        try:
            url = f"{self.api_url}/v1/transactions/{tx_hash}/info"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"Failed to verify transaction: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error verifying transaction: {e}")
            return None
    
    async def check_payment(self, amount: float, timeout: int = 1800) -> Optional[Dict]:
        """
        Monitor for incoming payment of specified amount
        Returns transaction details if payment found within timeout
        """
        start_time = asyncio.get_event_loop().time()
        last_checked_timestamp = start_time * 1000  # Convert to milliseconds
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                transactions = await self.get_account_transactions(self.wallet_address)
                
                if transactions:
                    for tx in transactions:
                        tx_timestamp = tx.get('block_timestamp', 0)
                        
                        # Only check transactions after we started monitoring
                        if tx_timestamp < last_checked_timestamp:
                            continue
                        
                        # Check if transaction is to our wallet
                        if tx.get('to') != self.wallet_address:
                            continue
                        
                        # Check if transaction is USDT TRC20
                        if tx.get('token_info', {}).get('address') != self.usdt_contract:
                            continue
                        
                        # Check amount (convert from smallest unit)
                        tx_amount = float(tx.get('value', 0)) / (10 ** tx.get('token_info', {}).get('decimals', 6))
                        
                        if abs(tx_amount - amount) < 0.01:  # Allow small difference
                            logger.info(f"Payment found: {tx.get('transaction_id')}")
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
                await asyncio.sleep(config.PAYMENT_CHECK_INTERVAL)
        
        return None
    
    async def verify_usdt_authenticity(self, tx_hash: str) -> bool:
        """
        Verify that the USDT transaction is real (not fake USDT)
        Checks if the token contract matches the official USDT TRC20 contract
        """
        try:
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                return False
            
            # Extract contract address from transaction
            contract_address = tx_info.get('trc20_transfer', [{}])[0].get('token_address', '')
            
            # Verify it's the official USDT contract
            if contract_address.upper() != self.usdt_contract.upper():
                logger.warning(f"Fake USDT detected! Contract: {contract_address}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying USDT authenticity: {e}")
            return False
    
    async def get_transaction_details(self, tx_hash: str) -> Optional[Dict]:
        """Get detailed information about a transaction"""
        try:
            tx_info = await self.verify_transaction(tx_hash)
            
            if not tx_info:
                return None
            
            # Extract relevant information
            trc20_transfers = tx_info.get('trc20_transfer', [])
            if not trc20_transfers:
                return None
            
            transfer = trc20_transfers[0]
            
            return {
                'tx_hash': tx_hash,
                'from': transfer.get('from_address', ''),
                'to': transfer.get('to_address', ''),
                'amount': float(transfer.get('amount_str', 0)) / 1000000,  # USDT has 6 decimals
                'token_address': transfer.get('token_address', ''),
                'timestamp': tx_info.get('block_timestamp', 0),
                'confirmed': tx_info.get('ret', [{}])[0].get('contractRet') == 'SUCCESS'
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            return None

# Global payment instance
tron_payment = TronPayment()
