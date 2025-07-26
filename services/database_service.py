import mysql.connector
from mysql.connector import pooling, Error
import logging
from typing import List, Optional, Dict
from config.settings import settings
from models.affiliate import Affiliate
from models.order import Order

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.pool = None
        self.create_pool()
    
    def create_pool(self):
        """Create database connection pool"""
        try:
            pool_config = {
                'pool_name': 'signal_automation_pool',
                'pool_size': settings.DB_POOL_SIZE,
                'pool_reset_session': True,
                'host': settings.DB_HOST,
                'database': settings.DB_NAME,
                'user': settings.DB_USER,
                'password': settings.DB_PASSWORD,
                'autocommit': False,
                'pool_timeout': settings.DB_POOL_TIMEOUT,
                'max_overflow': settings.DB_POOL_MAX_OVERFLOW
            }
            
            self.pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Database connection pool created with {settings.DB_POOL_SIZE} connections")
            
        except Error as e:
            logger.error(f"Database pool creation failed: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool"""
        try:
            return self.pool.get_connection()
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def create_affiliate(self, phone_number: str, token: str) -> Optional[int]:
        """Create new affiliate"""
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            query = "INSERT INTO affiliates (phone_number, token) VALUES (%s, %s)"
            cursor.execute(query, (phone_number, token))
            
            affiliate_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            
            logger.info(f"Created affiliate: {phone_number} with token: {token}")
            return affiliate_id
            
        except mysql.connector.IntegrityError as e:
            logger.warning(f"Affiliate already exists: {phone_number}")
            if connection:
                connection.rollback()
            return None
        except Error as e:
            logger.error(f"Error creating affiliate: {e}")
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                connection.close()
    
    def get_affiliate_by_phone(self, phone_number: str) -> Optional[Affiliate]:
        """Get affiliate by phone number"""
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM affiliates WHERE phone_number = %s AND is_active = TRUE"
            cursor.execute(query, (phone_number,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return Affiliate(**result)
            return None
            
        except Error as e:
            logger.error(f"Error getting affiliate by phone: {e}")
            return None
        finally:
            if connection:
                connection.close()
    
    def get_affiliate_by_token(self, token: str) -> Optional[Affiliate]:
        """Get affiliate by token"""
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM affiliates WHERE token = %s AND is_active = TRUE"
            cursor.execute(query, (token,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return Affiliate(**result)
            return None
            
        except Error as e:
            logger.error(f"Error getting affiliate by token: {e}")
            return None
        finally:
            if connection:
                connection.close()
    
    def get_unnotified_orders(self) -> List[Order]:
        """Get orders that haven't been notified"""
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = "SELECT * FROM orders WHERE notified = FALSE ORDER BY created_at ASC"
            cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            return [Order(**row) for row in results]
            
        except Error as e:
            logger.error(f"Error getting unnotified orders: {e}")
            return []
        finally:
            if connection:
                connection.close()
    
    def mark_order_as_notified(self, order_id: int) -> bool:
        """Mark order as notified"""
        connection = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            query = "UPDATE orders SET notified = TRUE WHERE id = %s"
            cursor.execute(query, (order_id,))
            
            connection.commit()
            cursor.close()
            
            logger.info(f"Marked order {order_id} as notified")
            return True
            
        except Error as e:
            logger.error(f"Error marking order as notified: {e}")
            if connection:
                connection.rollback()
            return False
        finally:
            if connection:
                connection.close()
    
    def close_pool(self):
        """Close all connections in pool"""
        if self.pool:
            # Note: mysql-connector-python doesn't have a direct close_all method
            # The pool will be garbage collected when the object is destroyed
            logger.info("Database connection pool closed")
