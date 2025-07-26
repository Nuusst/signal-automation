import logging
from typing import Dict
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
