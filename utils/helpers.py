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
