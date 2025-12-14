from pymongo import MongoClient
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = MongoClient(config.MONGODB_URI)
        self.db = self.client[config.MONGODB_DB]
        self.users = self.db.users
        self.orders = self.db.orders
        self.transactions = self.db.transactions
        self.settings = self.db.settings
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        self.users.create_index('user_id', unique=True)
        self.orders.create_index('order_id', unique=True)
        self.orders.create_index('user_id')
        self.orders.create_index('status')
        self.transactions.create_index('tx_hash', unique=True)
        self.transactions.create_index('order_id')
    
    # User operations
    def create_user(self, user_id, username=None, first_name=None):
        """Create or update user"""
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        self.users.update_one(
            {'user_id': user_id},
            {'$set': user_data},
            upsert=True
        )
        return user_data
    
    def get_user(self, user_id):
        """Get user by user_id"""
        return self.users.find_one({'user_id': user_id})
    
    # Order operations
    def create_order(self, order_id, user_id, months, price):
        """Create a new order"""
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'months': months,
            'price': price,
            'status': 'pending',  # pending, paid, completed, failed, expired
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'payment_address': config.PAYMENT_WALLET_ADDRESS,
            'expires_at': datetime.now().timestamp() + config.PAYMENT_TIMEOUT
        }
        self.orders.insert_one(order_data)
        return order_data
    
    def get_order(self, order_id):
        """Get order by order_id"""
        return self.orders.find_one({'order_id': order_id})
    
    def update_order_status(self, order_id, status, tx_hash=None):
        """Update order status"""
        update_data = {
            'status': status,
            'updated_at': datetime.now()
        }
        if tx_hash:
            update_data['tx_hash'] = tx_hash
        if status == 'completed':
            update_data['completed_at'] = datetime.now()
        
        self.orders.update_one(
            {'order_id': order_id},
            {'$set': update_data}
        )
    
    def get_pending_orders(self):
        """Get all pending orders"""
        return list(self.orders.find({'status': 'pending'}))
    
    def get_user_orders(self, user_id):
        """Get all orders for a user"""
        return list(self.orders.find({'user_id': user_id}).sort('created_at', -1))
    
    # Transaction operations
    def create_transaction(self, tx_hash, order_id, amount, from_address):
        """Record a transaction"""
        tx_data = {
            'tx_hash': tx_hash,
            'order_id': order_id,
            'amount': amount,
            'from_address': from_address,
            'created_at': datetime.now()
        }
        try:
            self.transactions.insert_one(tx_data)
            return tx_data
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
    
    def get_transaction(self, tx_hash):
        """Get transaction by hash"""
        return self.transactions.find_one({'tx_hash': tx_hash})
    
    def get_transaction_by_order(self, order_id):
        """Get transaction by order_id"""
        return self.transactions.find_one({'order_id': order_id})
    
    # Settings operations
    def get_setting(self, key):
        """Get a setting value"""
        setting = self.settings.find_one({'key': key})
        return setting['value'] if setting else None
    
    def set_setting(self, key, value):
        """Set a setting value"""
        self.settings.update_one(
            {'key': key},
            {'$set': {'key': key, 'value': value, 'updated_at': datetime.now()}},
            upsert=True
        )
    
    def get_prices(self):
        """Get current prices from database or config"""
        prices = {}
        for months in [3, 6, 12]:
            price = self.get_setting(f'price_{months}m')
            prices[months] = float(price) if price else config.PRICES[months]
        return prices
    
    def set_price(self, months, price):
        """Set price for a package"""
        self.set_setting(f'price_{months}m', price)

# Global database instance
db = Database()
