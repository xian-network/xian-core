"""
Plugin Manager for State Divergence Debugger

Manages loading, initialization, and lifecycle of debugger plugins.
"""

import importlib
from typing import Dict, Any, Type, Optional
from loguru import logger

from .config import DebuggerConfig
from .events import EventBus
from ..monitors.base import BaseMonitor
from ..analyzers.base import BaseAnalyzer
from ..reporters.base import BaseReporter


class PluginManager:
    """Manages debugger plugins"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.loaded_plugins: Dict[str, Any] = {}
        
        # Plugin registry - maps plugin names to their module paths
        self.plugin_registry = {
            # Monitors (all implemented and working)
            'state_tracker': 'xian.debugger.monitors.state_tracker',
            'cache_monitor': 'xian.debugger.monitors.cache_monitor',
            'json_validator': 'xian.debugger.monitors.json_validator',
            'determinism_validator': 'xian.debugger.monitors.determinism_validator',
            'crash_detector': 'xian.debugger.monitors.crash_detector',
            
            # Reporters (only implemented ones)
            'log_reporter': 'xian.debugger.reporters.log_reporter',
            
            # Note: Additional analyzers and reporters can be added here as they are implemented
            # 'divergence_analyzer': 'xian.debugger.analyzers.divergence_analyzer',
            # 'replay_analyzer': 'xian.debugger.analyzers.replay_analyzer',
            # 'file_reporter': 'xian.debugger.reporters.file_reporter',
            # 'webhook_reporter': 'xian.debugger.reporters.webhook_reporter'
        }
    
    def load_plugin(self, plugin_name: str, config: DebuggerConfig) -> Any:
        """Load and initialize a plugin"""
        if plugin_name in self.loaded_plugins:
            logger.debug(f"Plugin {plugin_name} already loaded")
            return self.loaded_plugins[plugin_name]
        
        if plugin_name not in self.plugin_registry:
            raise ValueError(f"Unknown plugin: {plugin_name}")
        
        module_path = self.plugin_registry[plugin_name]
        
        try:
            # Import the plugin module
            module = importlib.import_module(module_path)
            
            # Get the plugin class (assumes class name follows convention)
            class_name = self._get_plugin_class_name(plugin_name)
            plugin_class = getattr(module, class_name)
            
            # Initialize the plugin
            plugin_instance = plugin_class(config, self.event_bus)
            
            # Store the loaded plugin
            self.loaded_plugins[plugin_name] = plugin_instance
            
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return plugin_instance
            
        except ImportError as e:
            logger.error(f"Failed to import plugin {plugin_name}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Plugin {plugin_name} missing expected class {class_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
            raise
    
    def _get_plugin_class_name(self, plugin_name: str) -> str:
        """Convert plugin name to expected class name"""
        # Convert snake_case to PascalCase
        parts = plugin_name.split('_')
        return ''.join(word.capitalize() for word in parts)
    
    def unload_plugin(self, plugin_name: str):
        """Unload a plugin"""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            
            # Stop the plugin if it has a stop method
            if hasattr(plugin, 'stop'):
                try:
                    plugin.stop()
                except Exception as e:
                    logger.error(f"Error stopping plugin {plugin_name}: {e}")
            
            del self.loaded_plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Get a loaded plugin instance"""
        return self.loaded_plugins.get(plugin_name)
    
    def get_loaded_plugins(self) -> Dict[str, Any]:
        """Get all loaded plugins"""
        return self.loaded_plugins.copy()
    
    def register_plugin(self, plugin_name: str, module_path: str):
        """Register a new plugin"""
        self.plugin_registry[plugin_name] = module_path
        logger.info(f"Registered plugin: {plugin_name} -> {module_path}")
    
    def unregister_plugin(self, plugin_name: str):
        """Unregister a plugin"""
        if plugin_name in self.plugin_registry:
            # Unload if currently loaded
            if plugin_name in self.loaded_plugins:
                self.unload_plugin(plugin_name)
            
            del self.plugin_registry[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
    
    def reload_plugin(self, plugin_name: str, config: DebuggerConfig) -> Any:
        """Reload a plugin"""
        if plugin_name in self.loaded_plugins:
            self.unload_plugin(plugin_name)
        
        # Force module reload
        if plugin_name in self.plugin_registry:
            module_path = self.plugin_registry[plugin_name]
            if module_path in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[module_path])
        
        return self.load_plugin(plugin_name, config)
    
    def get_available_plugins(self) -> Dict[str, str]:
        """Get all available plugins"""
        return self.plugin_registry.copy()
    
    def shutdown(self):
        """Shutdown all plugins"""
        for plugin_name in list(self.loaded_plugins.keys()):
            self.unload_plugin(plugin_name)