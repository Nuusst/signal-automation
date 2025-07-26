import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Signal Configuration
    SIGNAL_NUMBER = os.getenv('SIGNAL_NUMBER')
    SIGNAL_GROUP_ID = os.getenv('SIGNAL_GROUP_ID')
    AFFILIATE_LINK = os.getenv('AFFILIATE_LINK')
    ADMIN_PHONE_NUMBER = os.getenv('ADMIN_PHONE_NUMBER')
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'database_card_store')
    DB_USER = os.getenv('DB_USER', 'signal_automation')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Database Pool Configuration
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    DB_POOL_MAX_OVERFLOW = int(os.getenv('DB_POOL_MAX_OVERFLOW', 5))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', 30))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', 3600))
    
    # Webhook Configuration
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    WEBHOOK_ENABLED = os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true'
    WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', 10))
    WEBHOOK_RETRIES = int(os.getenv('WEBHOOK_RETRIES', 3))
    
    # Application Settings
    POLL_INTERVAL_SECONDS = int(os.getenv('POLL_INTERVAL_SECONDS', 5))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    TOKEN_LENGTH = int(os.getenv('TOKEN_LENGTH', 12))
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Paris')
    
    # File Paths
    TEMPLATES_FILE = os.getenv('TEMPLATES_FILE', '/opt/signal-automation/config/templates.yaml')
    LOG_DIR = os.getenv('LOG_DIR', '/opt/signal-automation/logs')
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        required = [
            'SIGNAL_NUMBER', 'SIGNAL_GROUP_ID', 'AFFILIATE_LINK', 
            'ADMIN_PHONE_NUMBER', 'DB_PASSWORD'
        ]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Validate webhook settings if enabled
        if cls.WEBHOOK_ENABLED and not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when WEBHOOK_ENABLED is true")

settings = Settings()
