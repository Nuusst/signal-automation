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
