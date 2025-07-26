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
