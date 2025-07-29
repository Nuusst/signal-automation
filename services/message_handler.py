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
        # State management for API key registration
        self.api_key_registration_state = {}  # {sender: state}
        self.api_key_temp_data = {}  # {sender: {key_id, key}}
    
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
            return
        
        # Check if message is "New API key" from admin
        if body == "New API key" and sender == settings.ADMIN_PHONE_NUMBER:
            self._handle_api_key_registration_start(sender)
            return
        
        # Check if sender is in API key registration flow
        if sender in self.api_key_registration_state:
            self._handle_api_key_registration_step(sender, body)
            return
    
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
    
    def _handle_api_key_registration_start(self, sender: str):
        """Start API key registration flow"""
        try:
            # Set state to waiting for API key
            self.api_key_registration_state[sender] = "waiting_for_api_key"
            
            # Send request for API key
            message = "Okay, you want to register a new API key. Please enter the new key."
            self.signal_service.send_message(sender, message)
            
            logger.info(f"Started API key registration flow for admin {sender}")
            
        except Exception as e:
            logger.error(f"Error starting API key registration: {e}")
            self.alert_service.alert_critical_error(f"API key registration start error: {e}")
    
    def _handle_api_key_registration_step(self, sender: str, message: str):
        """Handle steps in API key registration flow"""
        try:
            state = self.api_key_registration_state.get(sender)
            
            if state == "waiting_for_api_key":
                self._handle_api_key_input(sender, message)
            elif state == "waiting_for_merchant_code":
                self._handle_merchant_code_input(sender, message)
                
        except Exception as e:
            logger.error(f"Error in API key registration step: {e}")
            self.alert_service.alert_critical_error(f"API key registration step error: {e}")
            # Clear state on error
            self.api_key_registration_state.pop(sender, None)
            self.api_key_temp_data.pop(sender, None)
    
    def _handle_api_key_input(self, sender: str, api_key: str):
        """Handle API key input and save to database"""
        try:
            # Save API key to database
            key_id = self.db_service.save_api_key(api_key)
            
            if key_id is None:
                # Error saving API key
                error_message = "Error saving API key to database. Please try again."
                self.signal_service.send_message(sender, error_message)
                # Clear state
                self.api_key_registration_state.pop(sender, None)
                return
            
            # Store temporary data
            self.api_key_temp_data[sender] = {
                'key_id': key_id,
                'key': api_key
            }
            
            # Update state to waiting for merchant code
            self.api_key_registration_state[sender] = "waiting_for_merchant_code"
            
            # Request merchant code
            message = "Key saved, please now enter merchant code."
            self.signal_service.send_message(sender, message)
            
            logger.info(f"API key saved for admin {sender}, waiting for merchant code")
            
        except Exception as e:
            logger.error(f"Error handling API key input: {e}")
            self.alert_service.alert_critical_error(f"API key input error: {e}")
            # Clear state on error
            self.api_key_registration_state.pop(sender, None)
            self.api_key_temp_data.pop(sender, None)
    
    def _handle_merchant_code_input(self, sender: str, merchant_code: str):
        """Handle merchant code input, generate token, and save to database"""
        try:
            # Get temporary data
            temp_data = self.api_key_temp_data.get(sender)
            if not temp_data:
                # This shouldn't happen, but just in case
                error_message = "Registration session expired. Please start over."
                self.signal_service.send_message(sender, error_message)
                # Clear state
                self.api_key_registration_state.pop(sender, None)
                return
            
            key_id = temp_data['key_id']
            
            # Save merchant code to database
            success = self.db_service.save_merchant_code(key_id, merchant_code)
            
            if not success:
                # Error saving merchant code
                error_message = "Error saving merchant code to database. Please try again."
                self.signal_service.send_message(sender, error_message)
                # Clear state
                self.api_key_registration_state.pop(sender, None)
                self.api_key_temp_data.pop(sender, None)
                return
            
            # Generate token
            token = generate_token(settings.TOKEN_LENGTH)
            
            # Save token to database
            success = self.db_service.save_token(key_id, token)
            
            if not success:
                # Error saving token
                error_message = "Error saving token to database. Please try again."
                self.signal_service.send_message(sender, error_message)
                # Clear state
                self.api_key_registration_state.pop(sender, None)
                self.api_key_temp_data.pop(sender, None)
                return
            
            # Send confirmation message
            confirmation_message = f"API key registration completed successfully! Token: {token}"
            self.signal_service.send_message(sender, confirmation_message)
            
            # Clear state
            self.api_key_registration_state.pop(sender, None)
            self.api_key_temp_data.pop(sender, None)
            
            logger.info(f"API key registration completed for admin {sender}")
            
        except Exception as e:
            logger.error(f"Error handling merchant code input: {e}")
            self.alert_service.alert_critical_error(f"Merchant code input error: {e}")
            # Clear state on error
            self.api_key_registration_state.pop(sender, None)
            self.api_key_temp_data.pop(sender, None)
