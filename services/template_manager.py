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
