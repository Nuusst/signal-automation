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
