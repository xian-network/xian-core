"""
Base Monitor Class

Defines the interface and common functionality for all monitor plugins.
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger

from ..core.config import DebuggerConfig
from ..core.events import EventBus, DebugEvent


class BaseMonitor(ABC):
    """Base class for all monitor plugins"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.name = self.__class__.__name__
        self.is_running = False
        self.is_enabled = True
        
        # Threading support for continuous monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            'events_emitted': 0,
            'errors_encountered': 0,
            'start_time': None,
            'last_check_time': None
        }
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the monitor.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def check(self) -> None:
        """
        Perform a single monitoring check.
        
        This method should examine the system state and emit events
        if any issues are detected.
        """
        pass
    
    def start(self):
        """Start the monitor"""
        if self.is_running or not self.is_enabled:
            return
        
        logger.info(f"Starting monitor: {self.name}")
        
        if not self.initialize():
            logger.error(f"Failed to initialize monitor: {self.name}")
            return
        
        self.is_running = True
        self.stats['start_time'] = time.time()
        self._stop_event.clear()
        
        # Start monitoring thread if continuous monitoring is needed
        if self.should_run_continuously():
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name=f"{self.name}-monitor",
                daemon=True
            )
            self._monitor_thread.start()
        
        logger.info(f"Monitor started: {self.name}")
    
    def stop(self):
        """Stop the monitor"""
        if not self.is_running:
            return
        
        logger.info(f"Stopping monitor: {self.name}")
        
        self.is_running = False
        self._stop_event.set()
        
        # Wait for monitor thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
            if self._monitor_thread.is_alive():
                logger.warning(f"Monitor thread did not stop gracefully: {self.name}")
        
        self.cleanup()
        logger.info(f"Monitor stopped: {self.name}")
    
    def should_run_continuously(self) -> bool:
        """
        Determine if this monitor should run continuously in a background thread.
        
        Override this method to return True for monitors that need continuous operation.
        """
        return False
    
    def get_check_interval(self) -> float:
        """
        Get the interval between checks for continuous monitoring.
        
        Returns:
            float: Interval in seconds
        """
        return 1.0  # Default to 1 second
    
    def _monitor_loop(self):
        """Main monitoring loop for continuous monitors"""
        interval = self.get_check_interval()
        
        while not self._stop_event.is_set():
            try:
                start_time = time.time()
                self.check()
                self.stats['last_check_time'] = start_time
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0:
                    self._stop_event.wait(sleep_time)
                
            except Exception as e:
                self.stats['errors_encountered'] += 1
                logger.error(f"Error in monitor {self.name}: {e}")
                
                # Back off on errors
                self._stop_event.wait(min(interval * 2, 30))
    
    def emit_event(self, event: DebugEvent):
        """Emit a debug event"""
        self.stats['events_emitted'] += 1
        self.event_bus.emit(event)
    
    def cleanup(self):
        """
        Cleanup resources when stopping the monitor.
        
        Override this method to perform any necessary cleanup.
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics"""
        stats = self.stats.copy()
        stats['name'] = self.name
        stats['is_running'] = self.is_running
        stats['is_enabled'] = self.is_enabled
        
        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
        
        return stats
    
    def enable(self):
        """Enable the monitor"""
        self.is_enabled = True
        logger.info(f"Monitor enabled: {self.name}")
    
    def disable(self):
        """Disable the monitor"""
        if self.is_running:
            self.stop()
        self.is_enabled = False
        logger.info(f"Monitor disabled: {self.name}")
    
    def is_healthy(self) -> bool:
        """
        Check if the monitor is healthy.
        
        Returns:
            bool: True if monitor is healthy, False otherwise
        """
        if not self.is_running:
            return False
        
        # Check if we've had too many errors
        error_rate = self.stats['errors_encountered'] / max(1, self.stats['events_emitted'])
        if error_rate > 0.1:  # More than 10% error rate
            return False
        
        # Check if we've checked recently (for continuous monitors)
        if self.should_run_continuously():
            last_check = self.stats.get('last_check_time')
            if last_check and time.time() - last_check > self.get_check_interval() * 5:
                return False
        
        return True


class EventDrivenMonitor(BaseMonitor):
    """
    Base class for monitors that respond to specific events rather than
    running continuously.
    """
    
    def should_run_continuously(self) -> bool:
        """Event-driven monitors don't run continuously"""
        return False
    
    def start(self):
        """Start event-driven monitor by registering event handlers"""
        if self.is_running or not self.is_enabled:
            return
        
        logger.info(f"Starting event-driven monitor: {self.name}")
        
        if not self.initialize():
            logger.error(f"Failed to initialize monitor: {self.name}")
            return
        
        self.is_running = True
        self.stats['start_time'] = time.time()
        
        # Register event handlers
        self.register_event_handlers()
        
        logger.info(f"Event-driven monitor started: {self.name}")
    
    def stop(self):
        """Stop event-driven monitor by unregistering event handlers"""
        if not self.is_running:
            return
        
        logger.info(f"Stopping event-driven monitor: {self.name}")
        
        self.is_running = False
        
        # Unregister event handlers
        self.unregister_event_handlers()
        
        self.cleanup()
        logger.info(f"Event-driven monitor stopped: {self.name}")
    
    @abstractmethod
    def register_event_handlers(self):
        """Register event handlers with the event bus"""
        pass
    
    @abstractmethod
    def unregister_event_handlers(self):
        """Unregister event handlers from the event bus"""
        pass
    
    def check(self):
        """Event-driven monitors don't need periodic checks"""
        pass