"""
Crash Detection Monitor

Monitors for application crashes, exceptions, and unexpected terminations
to help identify the root cause of state divergence issues.
"""

import os
import sys
import signal
import traceback
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from .base import BaseMonitor


class CrashDetector(BaseMonitor):
    """Monitor for detecting and analyzing application crashes"""
    
    def __init__(self, config, event_bus):
        super().__init__(config, event_bus)
        self.crash_log_file = self.config.log_directory / "crash_log.json"
        self.exception_count = 0
        self.last_operations: List[Dict[str, Any]] = []
        self.max_operation_history = 100
        self.crash_handlers_installed = False
        
    def initialize(self):
        """Initialize crash detection"""
        logger.info("Initializing Crash Detector")
        self._install_crash_handlers()
        self._start_health_monitor()
        return True
    
    def check(self):
        """Perform crash detection check"""
        # This is called periodically by the base monitor
        # Most crash detection is event-driven (signals, exceptions)
        # but we can use this for periodic health checks
        try:
            self._check_memory_usage()
            self._check_thread_count()
            self._check_file_descriptors()
        except Exception as e:
            logger.error(f"Error during crash detection check: {e}")
        
    def _install_crash_handlers(self):
        """Install signal handlers to detect crashes"""
        if self.crash_handlers_installed:
            return
            
        try:
            # Handle common crash signals
            signal.signal(signal.SIGTERM, self._handle_crash_signal)
            signal.signal(signal.SIGINT, self._handle_crash_signal)
            if hasattr(signal, 'SIGQUIT'):
                signal.signal(signal.SIGQUIT, self._handle_crash_signal)
            if hasattr(signal, 'SIGSEGV'):
                signal.signal(signal.SIGSEGV, self._handle_crash_signal)
            if hasattr(signal, 'SIGABRT'):
                signal.signal(signal.SIGABRT, self._handle_crash_signal)
                
            # Install exception hook
            sys.excepthook = self._handle_uncaught_exception
            
            self.crash_handlers_installed = True
            logger.debug("Crash handlers installed successfully")
            
        except Exception as e:
            logger.error(f"Failed to install crash handlers: {e}")
    
    def _handle_crash_signal(self, signum, frame):
        """Handle crash signals"""
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        
        crash_info = {
            "timestamp": datetime.now().isoformat(),
            "type": "signal",
            "signal": signal_name,
            "signal_number": signum,
            "recent_operations": self.last_operations[-10:],  # Last 10 operations
            "stack_trace": self._get_stack_trace(frame),
            "process_info": self._get_process_info()
        }
        
        logger.critical(f"Application crash detected - Signal {signal_name} ({signum})")
        self._log_crash(crash_info)
        
        # Call original handler if it exists
        if signum in [signal.SIGTERM, signal.SIGINT]:
            sys.exit(1)
    
    def _handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts as crashes
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        crash_info = {
            "timestamp": datetime.now().isoformat(),
            "type": "exception",
            "exception_type": exc_type.__name__,
            "exception_message": str(exc_value),
            "recent_operations": self.last_operations[-10:],
            "stack_trace": traceback.format_exception(exc_type, exc_value, exc_traceback),
            "process_info": self._get_process_info()
        }
        
        logger.critical(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
        self._log_crash(crash_info)
        
        # Call original exception hook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    def _get_stack_trace(self, frame=None):
        """Get current stack trace"""
        if frame:
            return traceback.format_stack(frame)
        else:
            return traceback.format_stack()
    
    def _get_process_info(self):
        """Get current process information"""
        try:
            import psutil
            process = psutil.Process()
            return {
                "pid": process.pid,
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
        except ImportError:
            return {
                "pid": os.getpid(),
                "memory_mb": "unknown",
                "cpu_percent": "unknown"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _log_crash(self, crash_info: Dict[str, Any]):
        """Log crash information"""
        try:
            import json
            
            # Append to crash log file
            with open(self.crash_log_file, 'a') as f:
                f.write(json.dumps(crash_info) + '\n')
                
            # Also emit as event for other monitors
            self.emit_event("application_crash", crash_info)
            
        except Exception as e:
            logger.error(f"Failed to log crash information: {e}")
    
    def _start_health_monitor(self):
        """Start background health monitoring"""
        def health_check():
            while self.running:
                try:
                    # Check for memory leaks
                    self._check_memory_usage()
                    
                    # Check for thread leaks
                    self._check_thread_count()
                    
                    # Check for file descriptor leaks
                    self._check_file_descriptors()
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        health_thread = threading.Thread(target=health_check, daemon=True)
        health_thread.start()
        logger.debug("Health monitor started")
    
    def _check_memory_usage(self):
        """Check for excessive memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.performance.max_memory_mb * 2:  # 2x the limit
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB")
                self.emit_event("high_memory_usage", {
                    "memory_mb": memory_mb,
                    "limit_mb": self.config.performance.max_memory_mb,
                    "recent_operations": self.last_operations[-5:]
                })
                
        except ImportError:
            pass  # psutil not available
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")
    
    def _check_thread_count(self):
        """Check for thread leaks"""
        try:
            import psutil
            process = psutil.Process()
            thread_count = process.num_threads()
            
            if thread_count > 50:  # Arbitrary threshold
                logger.warning(f"High thread count detected: {thread_count}")
                self.emit_event("high_thread_count", {
                    "thread_count": thread_count,
                    "recent_operations": self.last_operations[-5:]
                })
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Thread check failed: {e}")
    
    def _check_file_descriptors(self):
        """Check for file descriptor leaks"""
        try:
            import psutil
            process = psutil.Process()
            fd_count = len(process.open_files())
            
            if fd_count > 100:  # Arbitrary threshold
                logger.warning(f"High file descriptor count: {fd_count}")
                self.emit_event("high_fd_count", {
                    "fd_count": fd_count,
                    "recent_operations": self.last_operations[-5:]
                })
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"FD check failed: {e}")
    
    def record_operation(self, operation: str, context: Dict[str, Any]):
        """Record an operation for crash analysis"""
        operation_record = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "context": context
        }
        
        self.last_operations.append(operation_record)
        
        # Keep only recent operations
        if len(self.last_operations) > self.max_operation_history:
            self.last_operations = self.last_operations[-self.max_operation_history:]
    
    def on_event(self, event_type: str, data: Dict[str, Any]):
        """Handle events from other monitors"""
        # Record all events as operations for crash analysis
        self.record_operation(f"event_{event_type}", data)
        
        # Look for patterns that might indicate impending crashes
        if event_type in ["state_change", "commit", "finalize_block"]:
            self._analyze_crash_patterns(event_type, data)
    
    def _analyze_crash_patterns(self, event_type: str, data: Dict[str, Any]):
        """Analyze patterns that might indicate crashes"""
        try:
            # Check for rapid state changes (might indicate instability)
            recent_state_changes = [
                op for op in self.last_operations[-20:]
                if op.get("operation") == "event_state_change"
            ]
            
            if len(recent_state_changes) > 10:  # More than 10 state changes recently
                logger.warning("Rapid state changes detected - potential instability")
                self.emit_event("rapid_state_changes", {
                    "count": len(recent_state_changes),
                    "timespan_seconds": 60  # Assuming within last minute
                })
            
            # Check for repeated errors
            error_operations = [
                op for op in self.last_operations[-10:]
                if "error" in op.get("operation", "").lower()
            ]
            
            if len(error_operations) > 3:
                logger.warning("Multiple errors detected - potential crash risk")
                self.emit_event("multiple_errors", {
                    "error_count": len(error_operations),
                    "errors": error_operations
                })
                
        except Exception as e:
            logger.debug(f"Crash pattern analysis failed: {e}")
    
    def get_crash_summary(self) -> Dict[str, Any]:
        """Get summary of crash detection data"""
        try:
            crash_count = 0
            if self.crash_log_file.exists():
                with open(self.crash_log_file, 'r') as f:
                    crash_count = len(f.readlines())
            
            return {
                "total_crashes": crash_count,
                "exception_count": self.exception_count,
                "recent_operations_count": len(self.last_operations),
                "handlers_installed": self.crash_handlers_installed,
                "health_monitoring": self.running
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up crash detector"""
        try:
            # Restore original exception hook
            sys.excepthook = sys.__excepthook__
            
            # Note: We don't restore signal handlers as they might be needed
            # by other parts of the application
            
            logger.debug("Crash detector cleaned up")
            
        except Exception as e:
            logger.error(f"Error during crash detector cleanup: {e}")