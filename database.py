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
        self.gifts = self.db.gifts  # Gift records
        self.user_states = self.db.user_states  # User conversation states
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        self.users.create_index('user_id', unique=True)
        self.orders.create_index('order_id', unique=True)
        self.orders.create_index('user_id')
        self.orders.create_index('status')
        self.orders.create_index('created_at')
        self.transactions.create_index('tx_hash', unique=True)
        self.transactions.create_index('order_id')
        self.gifts.create_index('order_id')
        self.gifts.create_index('sender_id')
        self.gifts.create_index('recipient_id')
        self.user_states.create_index('user_id', unique=True)
    
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
        # Initialize balance if not exists
        self.users.update_one(
            {'user_id': user_id},
            {
                '$set': user_data,
                '$setOnInsert': {'balance': 0.0}
            },
            upsert=True
        )
        return user_data
    
    def get_user(self, user_id):
        """Get user by user_id"""
        return self.users.find_one({'user_id': user_id})
    
    def get_user_balance(self, user_id):
        """Get user's balance"""
        user = self.get_user(user_id)
        if user:
            return user.get('balance', 0.0)
        return 0.0
    
    def update_user_balance(self, user_id, amount, operation='add'):
        """Update user balance
        
        Args:
            user_id: User ID
            amount: Amount to add or subtract
            operation: 'add' or 'subtract'
        
        Returns:
            New balance or None if insufficient funds
        """
        if operation == 'add':
            result = self.users.update_one(
                {'user_id': user_id},
                {'$inc': {'balance': amount}, '$set': {'updated_at': datetime.now()}}
            )
            user = self.get_user(user_id)
            return user.get('balance', 0.0) if user else None
        elif operation == 'subtract':
            # Check if sufficient balance
            user = self.get_user(user_id)
            if not user or user.get('balance', 0.0) < amount:
                return None
            
            result = self.users.update_one(
                {'user_id': user_id},
                {'$inc': {'balance': -amount}, '$set': {'updated_at': datetime.now()}}
            )
            user = self.get_user(user_id)
            return user.get('balance', 0.0) if user else None
        
        return None
    
    # Order operations
    def create_order(self, order_id, user_id, months, price, product_type='premium', 
                     product_quantity=None, recipient_id=None, recipient_username=None):
        """Create a new order"""
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'months': months,
            'price': price,
            'product_type': product_type,  # 'premium' or 'stars'
            'product_quantity': product_quantity,  # For stars
            'status': 'pending',  # pending, paid, completed, failed, expired, cancelled
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'payment_address': config.PAYMENT_WALLET_ADDRESS,
            'expires_at': datetime.now().timestamp() + config.PAYMENT_TIMEOUT,
            'recipient_id': recipient_id,  # For gifts
            'recipient_username': recipient_username
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
    
    # User state management
    def set_user_state(self, user_id, state, data=None):
        """Set user conversation state"""
        state_data = {
            'user_id': user_id,
            'state': state,
            'data': data or {},
            'updated_at': datetime.now()
        }
        self.user_states.update_one(
            {'user_id': user_id},
            {'$set': state_data},
            upsert=True
        )
    
    def get_user_state(self, user_id):
        """Get user conversation state"""
        return self.user_states.find_one({'user_id': user_id})
    
    def clear_user_state(self, user_id):
        """Clear user conversation state"""
        self.user_states.delete_one({'user_id': user_id})
    
    # Gift records
    def create_gift_record(self, order_id, sender_id, recipient_id, product_type, value):
        """Create a gift record"""
        gift_data = {
            'order_id': order_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'product_type': product_type,
            'value': value,  # months for premium, quantity for stars
            'created_at': datetime.now()
        }
        self.gifts.insert_one(gift_data)
        return gift_data
    
    def get_gifts_sent(self, user_id):
        """Get gifts sent by user"""
        return list(self.gifts.find({'sender_id': user_id}).sort('created_at', -1))
    
    def get_gifts_received(self, user_id):
        """Get gifts received by user"""
        return list(self.gifts.find({'recipient_id': user_id}).sort('created_at', -1))
    
    # Statistics methods
    def get_user_statistics(self, user_id):
        """Get statistics for a specific user"""
        orders = list(self.orders.find({'user_id': user_id}))
        
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o['status'] == 'completed'])
        pending_orders = len([o for o in orders if o['status'] in ['pending', 'paid']])
        failed_orders = len([o for o in orders if o['status'] in ['failed', 'cancelled', 'expired']])
        
        total_spent = sum(o['price'] for o in orders if o['status'] == 'completed')
        
        # Get balance
        balance = self.get_user_balance(user_id)
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'failed_orders': failed_orders,
            'total_spent': total_spent,
            'balance': balance
        }
    
    def get_order_statistics(self):
        """Get overall order statistics"""
        total = self.orders.count_documents({})
        pending = self.orders.count_documents({'status': 'pending'})
        paid = self.orders.count_documents({'status': 'paid'})
        completed = self.orders.count_documents({'status': 'completed'})
        failed = self.orders.count_documents({'status': {'$in': ['failed', 'cancelled', 'expired']}})
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'pending': pending,
            'paid': paid,
            'completed': completed,
            'failed': failed,
            'success_rate': success_rate
        }
    
    def get_income_statistics(self):
        """Get income statistics"""
        from datetime import timedelta
        
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # Today's income
        today_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': today_start}
        }))
        today_income = sum(o['price'] for o in today_orders)
        
        # Week's income
        week_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': week_start}
        }))
        week_income = sum(o['price'] for o in week_orders)
        
        # Month's income
        month_orders = list(self.orders.find({
            'status': 'completed',
            'completed_at': {'$gte': month_start}
        }))
        month_income = sum(o['price'] for o in month_orders)
        
        # Total income
        all_completed = list(self.orders.find({'status': 'completed'}))
        total_income = sum(o['price'] for o in all_completed)
        
        return {
            'today': today_income,
            'week': week_income,
            'month': month_income,
            'total': total_income
        }
    
    def get_user_count_statistics(self):
        """Get user count statistics"""
        from datetime import timedelta
        
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        
        total_users = self.users.count_documents({})
        
        # Today's new users
        today_users = self.users.count_documents({
            'created_at': {'$gte': today_start}
        })
        
        # Active users (users with at least one completed order)
        active_users = len(self.orders.distinct('user_id', {'status': 'completed'}))
        
        return {
            'total': total_users,
            'today': today_users,
            'active': active_users
        }
    
    def get_stars_prices(self):
        """Get stars prices from database or default"""
        prices = {}
        for stars in [100, 250, 500, 1000, 2500]:
            price = self.get_setting(f'stars_price_{stars}')
            prices[stars] = float(price) if price else stars * 0.01
        return prices
    
    def set_stars_price(self, stars, price):
        """Set price for stars package"""
        self.set_setting(f'stars_price_{stars}', price)

# Global database instance
db = Database()
