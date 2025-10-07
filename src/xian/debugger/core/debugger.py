"""
Main State Divergence Debugger

The central coordinator for all debugging activities, managing plugins,
events, and providing the main API for debugging operations.
"""

import time
import threading
import psutil
import os
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, timedelta
from loguru import logger

from .config import DebuggerConfig, DebugLevel
from .events import EventBus, DebugEvent, EventType, Severity, create_performance_warning_event
from .plugin_manager import PluginManager
from ..monitors.base import BaseMonitor
from ..analyzers.base import BaseAnalyzer
from ..reporters.base import BaseReporter


class DebugContext:
    """Context manager for debugging operations"""
    
    def __init__(self, debugger, operation_name: str, **context_data):
        self.debugger = debugger
        self.operation_name = operation_name
        self.context_data = context_data
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        # Emit operation start event
        self.debugger.emit_event('operation_start', {
            'operation': self.operation_name,
            'start_time': self.start_time,
            **self.context_data
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        # Emit operation end event
        event_data = {
            'operation': self.operation_name,
            'duration_ms': duration * 1000,
            'success': exc_type is None,
            **self.context_data
        }
        
        if exc_type:
            event_data.update({
                'exception_type': exc_type.__name__,
                'exception_message': str(exc_val)
            })
        
        self.debugger.emit_event('operation_end', event_data)


class StateDebugger:
    """
    Main state divergence debugger class.
    
    Coordinates all debugging activities including monitoring, analysis,
    and reporting of potential state divergence issues.
    """
    
    def __init__(self, config: Optional[DebuggerConfig] = None):
        self.config = config or DebuggerConfig()
        self.event_bus = EventBus()
        self.plugin_manager = PluginManager(self.event_bus)
        
        # Core components
        self.monitors: Dict[str, BaseMonitor] = {}
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.reporters: Dict[str, BaseReporter] = {}
        
        # Runtime state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.stats = {
            'events_processed': 0,
            'divergences_detected': 0,
            'cache_leaks_found': 0,
            'json_errors_caught': 0,
            'performance_warnings': 0
        }
        
        # Performance monitoring
        self._performance_thread: Optional[threading.Thread] = None
        self._stop_performance_monitoring = threading.Event()
        
        # Current context
        self.current_block_height: Optional[int] = None
        self.current_transaction_hash: Optional[str] = None
        self.node_id: Optional[str] = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the debugger components"""
        logger.info("Initializing State Divergence Debugger")
        
        # Set up event handlers
        self._setup_event_handlers()
        
        # Load and initialize plugins
        self._load_plugins()
        
        # Emit startup event
        startup_event = DebugEvent(
            event_type=EventType.DEBUGGER_START,
            severity=Severity.INFO,
            message=f"State Debugger initialized with {self.config.debug_level.value} level",
            data={
                'config': {
                    'debug_level': self.config.debug_level.value,
                    'monitoring_scope': self.config.monitoring_scope.value,
                    'enabled_plugins': self.config.enabled_plugins
                }
            }
        )
        self.event_bus.emit(startup_event)
    
    def _setup_event_handlers(self):
        """Set up event handlers for different event types"""
        self.event_bus.subscribe(EventType.STATE_DIVERGENCE, self._handle_state_divergence)
        self.event_bus.subscribe(EventType.CACHE_LEAK, self._handle_cache_leak)
        self.event_bus.subscribe(EventType.JSON_DECODE_FAILURE, self._handle_json_error)
        self.event_bus.subscribe(EventType.PERFORMANCE_WARNING, self._handle_performance_warning)
    
    def _load_plugins(self):
        """Load and initialize plugins based on configuration"""
        for plugin_name in self.config.enabled_plugins:
            try:
                plugin_instance = self.plugin_manager.load_plugin(plugin_name, self.config)
                
                # Register plugin with appropriate collection
                if hasattr(plugin_instance, 'check'):  # It's a monitor
                    self.monitors[plugin_name] = plugin_instance
                elif hasattr(plugin_instance, 'analyze'):  # It's an analyzer
                    self.analyzers[plugin_name] = plugin_instance
                elif hasattr(plugin_instance, 'generate_report'):  # It's a reporter
                    self.reporters[plugin_name] = plugin_instance
                
                logger.debug(f"Loaded plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
    
    def start(self):
        """Start the debugger"""
        if self.is_running:
            logger.warning("Debugger is already running")
            return
        
        if not self.config.enabled:
            logger.info("Debugger is disabled in configuration")
            return
        
        logger.info("Starting State Divergence Debugger")
        self.is_running = True
        self.start_time = datetime.now()
        
        # Start performance monitoring
        if self.config.performance.enable_async_processing:
            self._start_performance_monitoring()
        
        # Start all monitors
        for monitor in self.monitors.values():
            monitor.start()
        
        logger.info("State Divergence Debugger started successfully")
    
    def stop(self):
        """Stop the debugger"""
        if not self.is_running:
            return
        
        logger.info("Stopping State Divergence Debugger")
        self.is_running = False
        
        # Stop performance monitoring
        self._stop_performance_monitoring.set()
        if self._performance_thread:
            self._performance_thread.join(timeout=5)
        
        # Stop all monitors
        for monitor in self.monitors.values():
            monitor.stop()
        
        # Emit shutdown event
        shutdown_event = DebugEvent(
            event_type=EventType.DEBUGGER_STOP,
            severity=Severity.INFO,
            message="State Debugger stopped",
            data={
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'stats': self.stats.copy()
            }
        )
        self.event_bus.emit(shutdown_event)
        
        logger.info("State Divergence Debugger stopped")
    
    def _start_performance_monitoring(self):
        """Start background performance monitoring"""
        self._performance_thread = threading.Thread(
            target=self._performance_monitor_loop,
            daemon=True
        )
        self._performance_thread.start()
    
    def _performance_monitor_loop(self):
        """Background loop for performance monitoring"""
        process = psutil.Process(os.getpid())
        
        while not self._stop_performance_monitoring.is_set():
            try:
                # Check memory usage
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                if memory_mb > self.config.performance.max_memory_mb:
                    event = create_performance_warning_event(
                        f"Memory usage exceeded threshold: {memory_mb:.1f}MB",
                        "memory_usage_mb",
                        memory_mb,
                        self.config.performance.max_memory_mb
                    )
                    self.event_bus.emit(event)
                
                # Check CPU usage
                cpu_percent = process.cpu_percent()
                if cpu_percent > self.config.performance.max_cpu_percent:
                    event = create_performance_warning_event(
                        f"CPU usage exceeded threshold: {cpu_percent:.1f}%",
                        "cpu_percent",
                        cpu_percent,
                        self.config.performance.max_cpu_percent
                    )
                    self.event_bus.emit(event)
                
                # Sleep for monitoring interval
                self._stop_performance_monitoring.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                self._stop_performance_monitoring.wait(60)  # Wait longer on error
    
    # Event handlers
    def _handle_state_divergence(self, event: DebugEvent):
        """Handle state divergence events"""
        self.stats['divergences_detected'] += 1
        logger.critical(f"State divergence detected: {event.message}")
        
        # Trigger immediate analysis if configured
        if self.config.debug_level in [DebugLevel.VERBOSE, DebugLevel.FORENSIC]:
            self._trigger_divergence_analysis(event)
    
    def _handle_cache_leak(self, event: DebugEvent):
        """Handle cache leak events"""
        self.stats['cache_leaks_found'] += 1
        logger.warning(f"Cache leak detected: {event.message}")
    
    def _handle_json_error(self, event: DebugEvent):
        """Handle JSON decode error events"""
        self.stats['json_errors_caught'] += 1
        logger.error(f"JSON decode error: {event.message}")
    
    def _handle_performance_warning(self, event: DebugEvent):
        """Handle performance warning events"""
        self.stats['performance_warnings'] += 1
        logger.warning(f"Performance warning: {event.message}")
    
    def _trigger_divergence_analysis(self, event: DebugEvent):
        """Trigger detailed analysis for state divergence"""
        # This would trigger more detailed analysis
        # Implementation depends on specific analyzers
        pass
    
    # Context management
    def set_context(self, block_height: Optional[int] = None, 
                   transaction_hash: Optional[str] = None,
                   node_id: Optional[str] = None):
        """Set current debugging context"""
        self.current_block_height = block_height
        self.current_transaction_hash = transaction_hash
        self.node_id = node_id
    
    def get_context(self) -> Dict[str, Any]:
        """Get current debugging context"""
        return {
            'block_height': self.current_block_height,
            'transaction_hash': self.current_transaction_hash,
            'node_id': self.node_id,
            'timestamp': datetime.now().isoformat()
        }
    
    # Monitoring hooks - these are called by instrumented code
    def on_transaction_start(self, tx_hash: str, tx_data: Dict[str, Any]):
        """Called when transaction processing starts"""
        if not self.is_running:
            return
        
        self.current_transaction_hash = tx_hash
        
        event = DebugEvent(
            event_type=EventType.TRANSACTION_START,
            severity=Severity.INFO,
            message=f"Transaction processing started: {tx_hash[:16]}...",
            transaction_hash=tx_hash,
            block_height=self.current_block_height,
            data=tx_data
        )
        self.event_bus.emit(event)
    
    def on_transaction_end(self, tx_hash: str, result: Dict[str, Any]):
        """Called when transaction processing ends"""
        if not self.is_running:
            return
        
        event = DebugEvent(
            event_type=EventType.TRANSACTION_END,
            severity=Severity.INFO,
            message=f"Transaction processing completed: {tx_hash[:16]}...",
            transaction_hash=tx_hash,
            block_height=self.current_block_height,
            data=result
        )
        self.event_bus.emit(event)
        
        self.current_transaction_hash = None
    
    def on_block_start(self, block_height: int, block_data: Dict[str, Any]):
        """Called when block processing starts"""
        if not self.is_running:
            return
        
        self.current_block_height = block_height
        
        event = DebugEvent(
            event_type=EventType.BLOCK_START,
            severity=Severity.INFO,
            message=f"Block processing started: {block_height}",
            block_height=block_height,
            data=block_data
        )
        self.event_bus.emit(event)
    
    def on_block_end(self, block_height: int, app_hash: str):
        """Called when block processing ends"""
        if not self.is_running:
            return
        
        event = DebugEvent(
            event_type=EventType.BLOCK_END,
            severity=Severity.INFO,
            message=f"Block processing completed: {block_height}",
            block_height=block_height,
            data={'app_hash': app_hash}
        )
        self.event_bus.emit(event)
    
    def on_commit(self, block_height: int, app_hash: str):
        """Called when block is committed"""
        if not self.is_running:
            return
        
        event = DebugEvent(
            event_type=EventType.BLOCK_COMMIT,
            severity=Severity.INFO,
            message=f"Block committed: {block_height}",
            block_height=block_height,
            data={'app_hash': app_hash}
        )
        self.event_bus.emit(event)
        
        self.current_block_height = None
    
    # Analysis and reporting methods
    def get_stats(self) -> Dict[str, Any]:
        """Get debugger statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'config': {
                'debug_level': self.config.debug_level.value,
                'monitoring_scope': self.config.monitoring_scope.value,
                'enabled_plugins': self.config.enabled_plugins
            },
            'stats': self.stats.copy(),
            'context': self.get_context(),
            'event_counts': {
                'total_events': len(self.event_bus.event_history),
                'critical_events': len(self.event_bus.get_critical_events())
            }
        }
    
    def get_recent_events(self, limit: int = 100, 
                         event_type: Optional[EventType] = None) -> List[Dict[str, Any]]:
        """Get recent debug events"""
        events = self.event_bus.get_events(event_type=event_type, limit=limit)
        return [event.to_dict() for event in events]
    
    def get_critical_issues(self) -> List[Dict[str, Any]]:
        """Get critical issues that need attention"""
        critical_events = self.event_bus.get_critical_events()
        return [event.to_dict() for event in critical_events]
    
    def generate_report(self, report_type: str = "summary") -> Dict[str, Any]:
        """Generate a debugging report"""
        # This would be implemented by specific reporters
        # For now, return basic stats
        return {
            'report_type': report_type,
            'generated_at': datetime.now().isoformat(),
            'stats': self.get_stats(),
            'critical_issues': self.get_critical_issues(),
            'recent_events': self.get_recent_events(50)
        }
    
    # Plugin management
    def register_monitor(self, name: str, monitor: BaseMonitor):
        """Register a monitor plugin"""
        self.monitors[name] = monitor
        if self.is_running:
            monitor.start()
    
    def register_analyzer(self, name: str, analyzer: BaseAnalyzer):
        """Register an analyzer plugin"""
        self.analyzers[name] = analyzer
    
    def register_reporter(self, name: str, reporter: BaseReporter):
        """Register a reporter plugin"""
        self.reporters[name] = reporter
    
    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit a debugging event"""
        try:
            # Convert string event type to EventType enum if needed
            if isinstance(event_type, str):
                event_type_enum = getattr(EventType, event_type.upper(), EventType.CUSTOM)
            else:
                event_type_enum = event_type
            
            event = DebugEvent(
                event_type=event_type_enum,
                severity=Severity.INFO,
                message=f"Debug event: {event_type}",
                data=data
            )
            self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
    
    def debug_context(self, operation_name: str, **context_data):
        """Create a debug context for an operation"""
        return DebugContext(self, operation_name, **context_data)
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Global debugger instance
_global_debugger: Optional[StateDebugger] = None


def get_debugger() -> Optional[StateDebugger]:
    """Get the global debugger instance"""
    return _global_debugger


def initialize_debugger(config: Optional[DebuggerConfig] = None) -> StateDebugger:
    """Initialize the global debugger instance"""
    global _global_debugger
    if _global_debugger is None:
        _global_debugger = StateDebugger(config)
    return _global_debugger


def shutdown_debugger():
    """Shutdown the global debugger instance"""
    global _global_debugger
    if _global_debugger:
        _global_debugger.stop()
        _global_debugger = None