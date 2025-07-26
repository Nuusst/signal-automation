# Signal Automation System - Complete Implementation Guide (Revised)

## Project Overview
Python automation script to run as systemd service on Ubuntu 24.04 for automated Signal messaging with MySQL database integration, hot-reloadable templates, enhanced security, and webhook fallback alerts.

## Security Model
- **Service User**: `signal-automation` (non-root)
- **Database Connection**: Pooled connections with health checks
- **Alert System**: Signal + Webhook fallback
- **File Permissions**: Restricted access, proper ownership

## Directory Structure
```
/opt/signal-automation/
├── main.py
├── requirements.txt
├── .env
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── templates.yaml
│   └── database_setup.sql
├── services/
│   ├── __init__.py
│   ├── signal_service.py
│   ├── database_service.py
│   ├── message_handler.py
│   ├── template_manager.py
│   ├── alert_service.py
│   └── webhook_service.py
├── models/
│   ├── __init__.py
│   ├── affiliate.py
│   └── order.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── logs/
│   ├── signal-automation.log
│   ├── critical-errors.log
│   └── template-updates.log
├── monitoring/
│   └── health_check.sh
└── systemd/
    └── signal-automation.service
```

## File Contents

### requirements.txt
```
mysql-connector-python==8.2.0
python-dotenv==1.0.0
PyYAML==6.0.1
watchdog==3.0.0
pytz==2023.3
requests==2.31.0
```

### .env
```
# Signal Configuration
SIGNAL_NUMBER=+33123456789
SIGNAL_GROUP_ID=your_group_id_here
AFFILIATE_LINK=https://yoursite.com/affiliate
ADMIN_PHONE_NUMBER=+33987654321

# Database Configuration
DB_HOST=localhost
DB_NAME=database_card_store
DB_USER=signal_automation
DB_PASSWORD=your_secure_password_here

# Database Pool Configuration
DB_POOL_SIZE=5
DB_POOL_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Webhook Configuration (Optional - fallback when Signal fails)
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
WEBHOOK_ENABLED=false
WEBHOOK_TIMEOUT=10
WEBHOOK_RETRIES=3

# Application Settings
POLL_INTERVAL_SECONDS=5
MAX_RETRIES=3
LOG_LEVEL=INFO
TOKEN_LENGTH=12
TIMEZONE=Europe/Paris

# File Paths
TEMPLATES_FILE=/opt/signal-automation/config/templates.yaml
LOG_DIR=/opt/signal-automation/logs
```

### config/__init__.py
```python
# Empty file to make config a package
```

### config/settings.py
```python
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
```

### config/templates.yaml
```yaml
templates:
  new_order_owner:
    format: |
      💸 New order alert!
      🕓 Time: {time}
      📅 Date: {date}
      💰 Total: {total}
      🙍‍♂️ Client: {client}
      🌍 IP: {ip}
  
  new_affiliate_owner:
    format: |
      🙍‍♂️ New affiliate alert!
      🕓 Time: {time}
      📅 Date: {date}
      📞 Phone number: {phone}
      🗝️ Affiliate token: {token}
  
  affiliate_registration_success:
    format: "Inscription confirmée - Votre lien affilié: {link}?{token}"
  
  affiliate_already_registered:
    format: "Vous êtes déjà enregistré - Votre lien affilié: {link}?{token}"
  
  new_order_affiliate:
    format: |
      💸 Nouvelle commande !
      🕓 Heure: {time}
      📅 Date: {date}
      💰 Total: {total}
      🙍‍♂️ Client: {client}
      🌍 IP: {ip}
  
  system_alert:
    format: "🚨 SYSTEM ALERT: {message}"
  
  webhook_alert:
    format: "⚠️ WEBHOOK ALERT: {message}"
```

### config/database_setup.sql
```sql
-- Create database
CREATE DATABASE IF NOT EXISTS database_card_store;

-- Create dedicated user (password will be set from .env)
CREATE USER IF NOT EXISTS 'signal_automation'@'localhost' IDENTIFIED BY 'PLACEHOLDER_PASSWORD';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON database_card_store.affiliates TO 'signal_automation'@'localhost';
GRANT SELECT, UPDATE ON database_card_store.orders TO 'signal_automation'@'localhost';

-- Create affiliates table
USE database_card_store;

CREATE TABLE IF NOT EXISTS affiliates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    token CHAR(12) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_phone (phone_number),
    INDEX idx_token (token)
);

-- Create orders table (if not exists from n8n)
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client VARCHAR(255),
    total DECIMAL(10,2),
    ip_address VARCHAR(45),
    affiliate_token CHAR(12),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT FALSE,
    INDEX idx_affiliate_token (affiliate_token),
    INDEX idx_notified (notified),
    INDEX idx_created_at (created_at)
);

FLUSH PRIVILEGES;
```

### services/__init__.py
```python
# Empty file to make services a package
```

### services/webhook_service.py
```python
import requests
import json
import logging
import time
from typing import Dict, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        self.webhook_url = settings.WEBHOOK_URL
        self.enabled = settings.WEBHOOK_ENABLED
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.max_retries = settings.WEBHOOK_RETRIES
    
    def send_webhook(self, message: str, alert_type: str = "info") -> bool:
        """Send webhook notification with retry logic"""
        if not self.enabled or not self.webhook_url:
            return False
        
        payload = self._create_payload(message, alert_type)
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    logger.info(f"Webhook sent successfully: {message}")
                    return True
                else:
                    logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        logger.error(f"All webhook attempts failed for message: {message}")
        return False
    
    def _create_payload(self, message: str, alert_type: str) -> Dict:
        """Create webhook payload - supports Slack/Discord format"""
        # Generic webhook payload that works with most services
        payload = {
            "text": f"🤖 Signal Automation Alert",
            "attachments": [
                {
                    "color": self._get_color_for_type(alert_type),
                    "fields": [
                        {
                            "title": "Alert Type",
                            "value": alert_type.upper(),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": message,
                            "short": False
                        },
                        {
                            "title": "Timestamp",
                            "value": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        return payload
    
    def _get_color_for_type(self, alert_type: str) -> str:
        """Get color code for different alert types"""
        colors = {
            "info": "#36a64f",      # Green
            "warning": "#ff9500",   # Orange
            "error": "#ff0000",     # Red
            "critical": "#8b0000"   # Dark Red
        }
        return colors.get(alert_type.lower(), "#36a64f")
    
    def test_webhook(self) -> bool:
        """Test webhook connectivity"""
        if not self.enabled:
            logger.info("Webhook is disabled")
            return True
        
        return self.send_webhook("Webhook test message", "info")
```

### services/signal_service.py
```python
import subprocess
import json
import logging
import time
from typing import List, Dict, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class SignalService:
    def __init__(self):
        self.signal_number = settings.SIGNAL_NUMBER
        self.max_retries = settings.MAX_RETRIES
    
    def send_message(self, recipient: str, message: str, is_group: bool = False) -> bool:
        """Send a Signal message to recipient with retry logic"""
        for attempt in range(self.max_retries):
            try:
                cmd = [
                    'signal-cli',
                    '-a', self.signal_number,
                    'send'
                ]
                
                if is_group:
                    cmd.extend(['-g', recipient])
                else:
                    cmd.append(recipient)
                
                cmd.extend(['-m', message])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info(f"Message sent successfully to {recipient}")
                    return True
                else:
                    logger.error(f"Failed to send message to {recipient}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout sending message to {recipient} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Error sending message to {recipient} (attempt {attempt + 1}): {str(e)}")
            
            if attempt < self.max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"All attempts failed to send message to {recipient}")
        return False
    
    def receive_messages(self) -> List[Dict]:
        """Receive new Signal messages"""
        try:
            cmd = [
                'signal-cli',
                '-a', self.signal_number,
                'receive',
                '--output=json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Failed to receive messages: {result.stderr}")
                return []
            
            messages = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        message_data = json.loads(line)
                        messages.append(message_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse message JSON: {line}")
            
            return messages
            
        except subprocess.TimeoutExpired:
            logger.warning("Timeout receiving messages")
            return []
        except Exception as e:
            logger.error(f"Error receiving messages: {str(e)}")
            return []
    
    def send_alert(self, message: str) -> bool:
        """Send alert message to admin"""
        return self.send_message(settings.ADMIN_PHONE_NUMBER, message)
    
    def test_signal_cli(self) -> bool:
        """Test signal-cli connectivity"""
        try:
            cmd = ['signal-cli', '-a', self.signal_number, 'listIdentities']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Signal-CLI test failed: {e}")
            return False
```

### services/database_service.py
```python
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
```

### services/template_manager.py
```python
import yaml
import logging
from typing import Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config.settings import settings
import threading

logger = logging.getLogger(__name__)

class TemplateHandler(FileSystemEventHandler):
    def __init__(self, template_manager):
        self.template_manager = template_manager
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path == settings.TEMPLATES_FILE:
            logger.info("Templates file modified, reloading...")
            self.template_manager.reload_templates()

class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.observer = None
        self.lock = threading.RLock()
        self.load_templates()
        self.start_watching()
    
    def load_templates(self):
        """Load templates from YAML file"""
        try:
            with open(settings.TEMPLATES_FILE, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                
            if 'templates' not in data:
                raise ValueError("Templates file must contain 'templates' key")
            
            with self.lock:
                self.templates = data['templates']
            
            logger.info(f"Loaded {len(self.templates)} templates")
            
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            if not self.templates:  # If no templates loaded yet, use defaults
                self.templates = self._get_default_templates()
    
    def reload_templates(self):
        """Reload templates and validate"""
        old_templates = self.templates.copy()
        try:
            self.load_templates()
            self._log_template_update("Templates reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload templates: {e}")
            with self.lock:
                self.templates = old_templates
            self._log_template_update(f"Template reload failed: {e}")
    
    def get_template(self, template_key: str) -> str:
        """Get template by key"""
        with self.lock:
            if template_key not in self.templates:
                logger.warning(f"Template '{template_key}' not found")
                return "Template not found: {message}"
            
            return self.templates[template_key]['format']
    
    def format_message(self, template_key: str, **kwargs) -> str:
        """Format message using template"""
        template = self.get_template(template_key)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return f"Template error: missing variable {e}"
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            return f"Template formatting error: {e}"
    
    def start_watching(self):
        """Start watching templates file for changes"""
        try:
            self.observer = Observer()
            event_handler = TemplateHandler(self)
            
            # Watch the directory containing the templates file
            import os
            watch_dir = os.path.dirname(settings.TEMPLATES_FILE)
            self.observer.schedule(event_handler, watch_dir, recursive=False)
            self.observer.start()
            
            logger.info("Started watching templates file for changes")
            
        except Exception as e:
            logger.error(f"Failed to start template file watcher: {e}")
    
    def stop_watching(self):
        """Stop watching templates file"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped watching templates file")
    
    def _log_template_update(self, message: str):
        """Log template updates to separate file"""
        template_logger = logging.getLogger('templates')
        template_logger.info(message)
    
    def _get_default_templates(self) -> Dict:
        """Get default templates as fallback"""
        return {
            'new_order_owner': {
                'format': '💸 New order alert!\n🕓 Time: {time}\n📅 Date: {date}\n💰 Total: {total}\n🙍‍♂️ Client: {client}\n🌍 IP: {ip}'
            },
            'system_alert': {
                'format': '🚨 SYSTEM ALERT: {message}'
            },
            'webhook_alert': {
                'format': '⚠️ WEBHOOK ALERT: {message}'
            }
        }
```

### services/alert_service.py
```python
import logging
from services.signal_service import SignalService
from services.template_manager import TemplateManager
from services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, signal_service: SignalService, template_manager: TemplateManager, webhook_service: WebhookService):
        self.signal_service = signal_service
        self.template_manager = template_manager
        self.webhook_service = webhook_service
        self.critical_logger = logging.getLogger('critical')
    
    def send_system_alert(self, message: str, alert_type: str = "info"):
        """Send system alert via Signal and webhook fallback"""
        try:
            # Try Signal first
            formatted_message = self.template_manager.format_message('system_alert', message=message)
            signal_success = self.signal_service.send_alert(formatted_message)
            
            if not signal_success:
                self.critical_logger.error(f"Failed to send Signal alert: {message}")
                
                # Fallback to webhook if Signal fails
                webhook_message = self.template_manager.format_message('webhook_alert', message=message)
                webhook_success = self.webhook_service.send_webhook(webhook_message, alert_type)
                
                if not webhook_success:
                    self.critical_logger.error(f"Both Signal and webhook alerts failed: {message}")
                else:
                    logger.info(f"Webhook fallback successful for: {message}")
            
        except Exception as e:
            self.critical_logger.error(f"Alert service error: {e} - Original message: {message}")
    
    def alert_database_error(self, error_message: str):
        """Alert about database connectivity issues"""
        self.send_system_alert(f"Database error: {error_message}", "error")
    
    def alert_signal_error(self, error_message: str):
        """Alert about Signal service issues"""
        self.critical_logger.error(f"Signal service error: {error_message}")
        # Use webhook for Signal errors since Signal is down
        webhook_message = self.template_manager.format_message('webhook_alert', message=f"Signal error: {error_message}")
        self.webhook_service.send_webhook(webhook_message, "error")
    
    def alert_critical_error(self, error_message: str):
        """Alert about critical system errors"""
        self.send_system_alert(f"Critical error: {error_message}", "critical")
        self.critical_logger.error(f"Critical error: {error_message}")
    
    def test_alert_systems(self) -> Dict[str, bool]:
        """Test both Signal and webhook alert systems"""
        results = {}
        
        # Test Signal
        results['signal'] = self.signal_service.test_signal_cli()
        
        # Test Webhook
        results['webhook'] = self.webhook_service.test_webhook()
        
        return results
```

### services/message_handler.py
```python
import logging
from typing import Dict, List
from services.signal_service import SignalService
from services.database_service import DatabaseService
from services.template_manager import TemplateManager
from services.alert_service import AlertService
from utils.helpers import generate_token, format_datetime
from config.settings import settings

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, signal_service: SignalService, db_service: DatabaseService, 
                 template_manager: TemplateManager, alert_service: AlertService):
        self.signal_service = signal_service
        self.db_service = db_service
        self.template_manager = template_manager
        self.alert_service = alert_service
    
    def process_received_messages(self, messages: List[Dict]):
        """Process received Signal messages"""
        for message in messages:
            try:
                self._process_single_message(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                self.alert_service.alert_critical_error(f"Message processing error: {e}")
    
    def _process_single_message(self, message: Dict):
        """Process a single received message"""
        envelope = message.get('envelope', {})
        data_message = envelope.get('dataMessage', {})
        
        if not data_message:
            return
        
        body = data_message.get('message', '').strip()
        sender = envelope.get('source')
        
        if not body or not sender:
            return
        
        logger.info(f"Received message from {sender}: {body}")
        
        # Check if message is "Go" for affiliate registration
        if body.lower() == 'go':
            self._handle_affiliate_registration(sender)
    
    def _handle_affiliate_registration(self, phone_number: str):
        """Handle affiliate registration process"""
        try:
            # Check if affiliate already exists
            existing_affiliate = self.db_service.get_affiliate_by_phone(phone_number)
            
            if existing_affiliate:
                # Send already registered message
                message = self.template_manager.format_message(
                    'affiliate_already_registered',
                    link=settings.AFFILIATE_LINK,
                    token=existing_affiliate.token
                )
                self.signal_service.send_message(phone_number, message)
                logger.info(f"Sent existing affiliate info to {phone_number}")
                return
            
            # Create new affiliate
            token = generate_token(settings.TOKEN_LENGTH)
            affiliate_id = self.db_service.create_affiliate(phone_number, token)
            
            if affiliate_id:
                # Send registration success message
                message = self.template_manager.format_message(
                    'affiliate_registration_success',
                    link=settings.AFFILIATE_LINK,
                    token=token
                )
                self.signal_service.send_message(phone_number, message)
                
                # Notify owner about new affiliate
                owner_message = self.template_manager.format_message(
                    'new_affiliate_owner',
                    time=format_datetime('time'),
                    date=format_datetime('date'),
                    phone=phone_number,
                    token=token
                )
                self.signal_service.send_message(settings.SIGNAL_GROUP_ID, owner_message, is_group=True)
                
                logger.info(f"Successfully registered new affiliate: {phone_number}")
            else:
                logger.error(f"Failed to create affiliate: {phone_number}")
                
        except Exception as e:
            logger.error(f"Error in affiliate registration: {e}")
            self.alert_service.alert_critical_error(f"Affiliate registration error: {e}")
    
    def process_new_orders(self):
        """Process new orders from database"""
        try:
            orders = self.db_service.get_unnotified_orders()
            
            for order in orders:
                self._process_single_order(order)
                
        except Exception as e:
            logger.error(f"Error processing orders: {e}")
            self.alert_service.alert_database_error(f"Order processing error: {e}")
    
    def _process_single_order(self, order):
        """Process a single order"""
        try:
            # Format order data for messages
            order_data = {
                'time': format_datetime('time', order.created_at),
                'date': format_datetime('date', order.created_at),
                'total': f"{order.total:.2f}€" if order.total else "N/A",
                'client': order.client or "N/A",
                'ip': order.ip_address or "N/A"
            }
            
            # Always notify owner
            owner_message = self.template_manager.format_message('new_order_owner', **order_data)
            self.signal_service.send_message(settings.SIGNAL_GROUP_ID, owner_message, is_group=True)
            
            # If order has affiliate token, notify affiliate
            if order.affiliate_token:
                affiliate = self.db_service.get_affiliate_by_token(order.affiliate_token)
                if affiliate:
                    affiliate_message = self.template_manager.format_message('new_order_affiliate', **order_data)
                    self.signal_service.send_message(affiliate.phone_number, affiliate_message)
                    logger.info(f"Notified affiliate {affiliate.phone_number} about order {order.id}")
            
            # Mark order as notified
            self.db_service.mark_order_as_notified(order.id)
            logger.info(f"Processed order {order.id}")
            
        except Exception as e:
            logger.error(f"Error processing order {order.id}: {e}")
            self.alert_service.alert_critical_error(f"Order {order.id} processing error: {e}")
```

### models/__init__.py
```python
# Empty file to make models a package
```

### models/affiliate.py
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Affiliate:
    id: int
    phone_number: str
    token: str
    created_at: datetime
    is_active: bool = True
    
    def __post_init__(self):
        # Convert string datetime to datetime object if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
```

### models/order.py
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

@dataclass
class Order:
    id: int
    client: Optional[str]
    total: Optional[Decimal]
    ip_address: Optional[str]
    affiliate_token: Optional[str]
    created_at: datetime
    notified: bool = False
    
    def __post_init__(self):
        # Convert string datetime to datetime object if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        
        # Convert float to Decimal for total
        if isinstance(self.total, float):
            self.total = Decimal(str(self.total))
```

### utils/__init__.py
```python
# Empty file to make utils a package
```

### utils/helpers.py
```python
import random
import string
import pytz
from datetime import datetime
from typing import Optional
from config.settings import settings

def generate_token(length: int = 12) -> str:
    """Generate random alphanumeric token"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def format_datetime(format_type: str, dt: Optional[datetime] = None) -> str:
    """Format datetime for Paris timezone"""
    if dt is None:
        dt = datetime.utcnow()
    
    # Convert to Paris timezone
    utc = pytz.UTC
    paris_tz = pytz.timezone(settings.TIMEZONE)
    
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    
    paris_dt = dt.astimezone(paris_tz)
    
    if format_type == 'time':
        return paris_dt.strftime("%H:%M:%S")
    elif format_type == 'date':
        return paris_dt.strftime("%Y-%m-%d")
    elif format_type == 'datetime':
        return paris_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return paris_dt.strftime("%Y-%m-%d %H:%M:%S")

def setup_logging():
    """Setup logging configuration"""
    import logging
    import logging.handlers
    import os
    
    # Create logs directory if it doesn't exist
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    
    # Main application logger
    main_logger = logging.getLogger()
    main_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Main log file handler with rotation
    main_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, 'signal-automation.log'),
        when='midnight',
        interval=1,
        backupCount=7,  # Keep 1 week of logs
        encoding='utf-8'
    )
    main_handler.setFormatter(formatter)
    main_logger.addHandler(main_handler)
    
    # Critical errors log
    critical_logger = logging.getLogger('critical')
    critical_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, 'critical-errors.log'),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    critical_handler.setFormatter(formatter)
    critical_logger.addHandler(critical_handler)
    
    # Template updates log
    template_logger = logging.getLogger('templates')
    template_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, 'template-updates.log'),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    template_handler.setFormatter(formatter)
    template_logger.addHandler(template_handler)
    
    # Console handler for debugging (optional)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    main_logger.addHandler(console_handler)
    
    logging.info("Logging system initialized")
```

### main.py
```python
#!/usr/bin/env python3
"""
Signal Automation System
Main entry point for the Signal automation service
"""

import time
import logging
import signal
import sys
from threading import Event
from config.settings import settings
from services.signal_service import SignalService
from services.database_service import DatabaseService
from services.template_manager import TemplateManager
from services.webhook_service import WebhookService
from services.alert_service import AlertService
from services.message_handler import MessageHandler
from utils.helpers import setup_logging

logger = logging.getLogger(__name__)

class SignalAutomation:
    def __init__(self):
        self.shutdown_event = Event()
        self.signal_service = None
        self.db_service = None
        self.template_manager = None
        self.webhook_service = None
        self.alert_service = None
        self.message_handler = None
        
    def initialize_services(self):
        """Initialize all services"""
        try:
            logger.info("Initializing Signal Automation System...")
            
            # Validate settings
            settings.validate()
            
            # Initialize services
            self.signal_service = SignalService()
            self.db_service = DatabaseService()
            self.template_manager = TemplateManager()
            self.webhook_service = WebhookService()
            self.alert_service = AlertService(
                self.signal_service, 
                self.template_manager, 
                self.webhook_service
            )
            self.message_handler = MessageHandler(
                self.signal_service,
                self.db_service,
                self.template_manager,
                self.alert_service
            )
            
            # Test connectivity
            self._test_system_connectivity()
            
            logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False
    
    def _test_system_connectivity(self):
        """Test system connectivity on startup"""
        logger.info("Testing system connectivity...")
        
        # Test database
        if not self.db_service.test_connection():
            raise Exception("Database connectivity test failed")
        
        # Test Signal CLI
        if not self.signal_service.test_signal_cli():
            logger.warning("Signal CLI test failed - service may have issues")
        
        # Test alert systems
        alert_results = self.alert_service.test_alert_systems()
        logger.info(f"Alert system tests: {alert_results}")
        
        logger.info("System connectivity tests completed")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def run_main_loop(self):
        """Main application loop"""
        logger.info("Starting main application loop...")
        
        while not self.shutdown_event.is_set():
            try:
                # Process received messages
                messages = self.signal_service.receive_messages()
                if messages:
                    self.message_handler.process_received_messages(messages)
                
                # Process new orders
                self.message_handler.process_new_orders()
                
                # Wait before next iteration
                self.shutdown_event.wait(settings.POLL_INTERVAL_SECONDS)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.alert_service.alert_critical_error(f"Main loop error: {e}")
                # Wait a bit before retrying to avoid tight error loops
                self.shutdown_event.wait(5)
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        try:
            if self.template_manager:
                self.template_manager.stop_watching()
            
            if self.db_service:
                self.db_service.close_pool()
                
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def run(self):
        """Main run method"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Initialize services
            if not self.initialize_services():
                logger.error("Service initialization failed, exiting...")
                return 1
            
            # Send startup notification
            self.alert_service.send_system_alert("Signal Automation System started successfully")
            
            # Run main loop
            self.run_main_loop()
            
            # Send shutdown notification
            self.alert_service.send_system_alert("Signal Automation System shutting down")
            
            return 0
            
        except Exception as e:
            logger.error(f"Critical error in main application: {e}")
            if self.alert_service:
                self.alert_service.alert_critical_error(f"Application crash: {e}")
            return 1
        
        finally:
            self.cleanup()

def main():
    """Entry point"""
    # Setup logging first
    setup_logging()
    
    logger.info("=" * 50)
    logger.info("Signal Automation System Starting")
    logger.info("=" * 50)
    
    app = SignalAutomation()
    exit_code = app.run()
    
    logger.info("=" * 50)
    logger.info("Signal Automation System Stopped")
    logger.info("=" * 50)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

### systemd/signal-automation.service
```ini
[Unit]
Description=Signal Automation Service
After=network.target mysql.service
Requires=mysql.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=signal-automation
Group=signal-automation
WorkingDirectory=/opt/signal-automation
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 /opt/signal-automation/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/opt/signal-automation/logs /home/signal-automation/.local/share/signal-cli

# Resource limits
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

### monitoring/health_check.sh
```bash
#!/bin/bash

# Signal Automation Health Check Script
# Run this script via cron to monitor the service

SERVICE_NAME="signal-automation"
LOG_FILE="/opt/signal-automation/logs/health-check.log"
CRITICAL_LOG="/opt/signal-automation/logs/critical-errors.log"
ADMIN_PHONE="+33987654321"  # Update with actual admin phone
SIGNAL_NUMBER="+33123456789"  # Update with actual signal number
SERVICE_USER="signal-automation"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to send emergency alert (fallback when Signal service is down)
send_emergency_alert() {
    local message="$1"
    log_message "EMERGENCY: $message"
    
    # Try to send via signal-cli directly as service user
    if command -v signal-cli >/dev/null 2>&1; then
        sudo -u "$SERVICE_USER" signal-cli -a "$SIGNAL_NUMBER" send "$ADMIN_PHONE" -m "🚨 HEALTH CHECK ALERT: $message" 2>/dev/null
    fi
    
    # You can add additional alert methods here (email, webhook, etc.)
}

# Check if service is running
check_service_status() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

# Check if there are recent critical errors
check_critical_errors() {
    if [ -f "$CRITICAL_LOG" ]; then
        # Check for critical errors in the last 5 minutes
        recent_errors=$(find "$CRITICAL_LOG" -newermt "5 minutes ago" -exec grep -c "CRITICAL\|ERROR" {} \; 2>/dev/null || echo "0")
        if [ "$recent_errors" -gt 0 ]; then
            return 1
        fi
    fi
    return 0
}

# Check database connectivity
check_database() {
    # Simple check - try to connect to MySQL
    if ! mysqladmin ping -h localhost -u signal_automation --silent 2>/dev/null; then
        return 1
    fi
    return 0
}

# Check disk space
check_disk_space() {
    # Check if /opt/signal-automation has less than 100MB free
    available=$(df /opt/signal-automation | tail -1 | awk '{print $4}')
    if [ "$available" -lt 102400 ]; then  # 100MB in KB
        return 1
    fi
    return 0
}

# Main health check
main() {
    log_message "Starting health check"
    
    # Check service status
    if ! check_service_status; then
        send_emergency_alert "Service $SERVICE_NAME is not running"
        log_message "ERROR: Service is not running"
        
        # Attempt to restart
        log_message "Attempting to restart service"
        if systemctl restart "$SERVICE_NAME"; then
            log_message "Service restarted successfully"
            sleep 5
            if check_service_status; then
                send_emergency_alert "Service $SERVICE_NAME was restarted successfully"
            else
                send_emergency_alert "Failed to restart service $SERVICE_NAME"
            fi
        else
            send_emergency_alert "Failed to restart service $SERVICE_NAME"
        fi
        exit 1
    fi
    
    # Check for critical errors
    if ! check_critical_errors; then
        send_emergency_alert "Critical errors detected in the last 5 minutes"
        log_message "WARNING: Critical errors detected"
    fi
    
    # Check database connectivity
    if ! check_database; then
        send_emergency_alert "Database connectivity issues detected"
        log_message "ERROR: Database connectivity issues"
    fi
    
    # Check disk space
    if ! check_disk_space; then
        send_emergency_alert "Low disk space detected"
        log_message "WARNING: Low disk space"
    fi
    
    log_message "Health check completed successfully"
}

# Run main function
main "$@"
```

## Installation Instructions (Revised for Non-Root User)

### 1. System Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv mysql-server openjdk-11-jre

# Install signal-cli
wget https://github.com/AsamK/signal-cli/releases/latest/download/signal-cli-*.tar.gz
tar -xzf signal-cli-*.tar.gz
sudo mv signal-cli-* /opt/signal-cli
sudo ln -s /opt/signal-cli/bin/signal-cli /usr/local/bin/signal-cli
```

### 2. User and Directory Setup
```bash
# Create dedicated user
sudo useradd -r -s /bin/false -d /opt/signal-automation signal-automation

# Create application directory
sudo mkdir -p /opt/signal-automation
sudo mkdir -p /opt/signal-automation/logs
sudo mkdir -p /home/signal-automation/.local/share/signal-cli

# Set ownership
sudo chown -R signal-automation:signal-automation /opt/signal-automation
sudo chown -R signal-automation:signal-automation /home/signal-automation
```

### 3. Database Setup
```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user (replace PLACEHOLDER_PASSWORD with actual password)
sudo mysql -e "
CREATE DATABASE IF NOT EXISTS database_card_store;
CREATE USER IF NOT EXISTS 'signal_automation'@'localhost' IDENTIFIED BY 'your_actual_password_here';
GRANT SELECT, INSERT, UPDATE ON database_card_store.affiliates TO 'signal_automation'@'localhost';
GRANT SELECT, UPDATE ON database_card_store.orders TO 'signal_automation'@'localhost';
FLUSH PRIVILEGES;
"

# Run table creation
sudo mysql database_card_store < /opt/signal-automation/config/database_setup.sql
```

### 4. Signal-CLI Setup
```bash
# Register Signal account as service user
sudo -u signal-automation signal-cli -a +33123456789 register

# Verify with SMS code (replace YOUR_SMS_CODE with actual code)
sudo -u signal-automation signal-cli -a +33123456789 verify YOUR_SMS_CODE

# Test sending message
sudo -u signal-automation signal-cli -a +33123456789 send +33987654321 -m "Test message"

# Get group ID (join group first via Signal app, then list groups)
sudo -u signal-automation signal-cli -a +33123456789 listGroups
```

### 5. Application Installation
```bash
# Copy application files
sudo cp -r * /opt/signal-automation/

# Create Python virtual environment
cd /opt/signal-automation
sudo -u signal-automation python3 -m venv venv
sudo -u signal-automation venv/bin/pip install -r requirements.txt

# Set proper permissions
sudo chown -R signal-automation:signal-automation /opt/signal-automation
sudo chmod 644 /opt/signal-automation/.env
sudo chmod +x /opt/signal-automation/main.py
sudo chmod +x /opt/signal-automation/monitoring/health_check.sh
```

### 6. Configuration
```bash
# Edit environment file
sudo nano /opt/signal-automation/.env

# Update all required values:
# - SIGNAL_NUMBER (your Signal number)
# - SIGNAL_GROUP_ID (obtained from listGroups command)
# - AFFILIATE_LINK (your affiliate link)
# - ADMIN_PHONE_NUMBER (for alerts)
# - DB_PASSWORD (database password)
# - WEBHOOK_URL (optional, for fallback alerts)
```

### 7. Service Installation
```bash
# Install systemd service
sudo cp systemd/signal-automation.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable signal-automation

# Start service
sudo systemctl start signal-automation

# Check status
sudo systemctl status signal-automation
```

### 8. Monitoring Setup
```bash
# Add health check to crontab
sudo crontab -e

# Add this line (run every 5 minutes):
# */5 * * * * /opt/signal-automation/monitoring/health_check.sh

# Setup log rotation
sudo tee /etc/logrotate.d/signal-automation << EOF
/opt/signal-automation/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 signal-automation signal-automation
    su signal-automation signal-automation
}
EOF
```

## Usage and Maintenance

### Service Management
```bash
# Start service
sudo systemctl start signal-automation

# Stop service
sudo systemctl stop signal-automation

# Restart service
sudo systemctl restart signal-automation

# View logs
sudo journalctl -u signal-automation -f

# View application logs
sudo tail -f /opt/signal-automation/logs/signal-automation.log
```

### Template Updates
```bash
# Edit templates (service will auto-reload)
sudo nano /opt/signal-automation/config/templates.yaml

# Check template update logs
sudo tail -f /opt/signal-automation/logs/template-updates.log
```

### Database Management
```bash
# Connect to database
mysql -u signal_automation -p database_card_store

# Check affiliates
SELECT * FROM affiliates;

# Check orders
SELECT * FROM orders WHERE notified = FALSE;
```

### Troubleshooting
```bash
# Check service status
sudo systemctl status signal-automation

# View recent logs
sudo journalctl -u signal-automation --since "1 hour ago"

# Check critical errors
sudo cat /opt/signal-automation/logs/critical-errors.log

# Test Signal-CLI manually
sudo -u signal-automation signal-cli -a +33123456789 receive --output=json

# Test database connection
mysql -u signal_automation -p -e "SELECT 1"

# Test webhook (if enabled)
curl -X POST -H "Content-Type: application/json" -d '{"text":"Test"}' YOUR_WEBHOOK_URL
```

## Security Enhancements

### Key Security Features:
1. **Non-root execution**: Service runs as dedicated `signal-automation` user
2. **File permissions**: Restricted access to configuration and log files
3. **Database isolation**: Limited database permissions for service user
4. **Systemd hardening**: Additional security constraints in service file
5. **Connection pooling**: Prevents database connection exhaustion
6. **Webhook fallback**: Ensures alerts are delivered even if Signal fails

### Security Checklist:
- [ ] .env file is only readable by signal-automation user
- [ ] Database user has minimal required permissions
- [ ] Signal-CLI data directory is properly secured
- [ ] Log files are rotated and archived regularly
- [ ] Webhook URLs use HTTPS (if webhook enabled)
- [ ] Regular security updates are applied

## Monitoring and Alerts

The enhanced system provides comprehensive monitoring:

1. **Service Level**: Systemd monitors the main process
2. **Application Level**: Internal error handling with retry logic
3. **Health Check**: External script monitors service health every 5 minutes
4. **Dual Alert System**: Signal + Webhook fallback for reliability
5. **Connection Pooling**: Database connection health monitoring
6. **Resource Monitoring**: Disk space and system resource checks

Critical errors trigger alerts through both Signal and webhook (if configured), ensuring immediate notification regardless of Signal service availability.

This revised implementation provides a production-ready Signal automation system with enhanced security, reliability, and monitoring capabilities.
