"""
Integration Example

Shows how to integrate the state divergence debugger with the existing
Xian ABCI application.
"""

from typing import Optional
from loguru import logger

from .core.debugger import StateDebugger, initialize_debugger, get_debugger
from .core.config import DebuggerConfig, DebugLevel, MonitoringScope
from .utils.instrumentation import (
    instrument_abci_method,
    instrument_transaction_processing,
    instrument_json_operations,
    instrument_cache_operations,
    DebuggerContext
)


class DebuggerIntegration:
    """
    Helper class for integrating the debugger with existing Xian code.
    """
    
    def __init__(self, config: Optional[DebuggerConfig] = None):
        self.config = config or self._create_default_config()
        self.debugger: Optional[StateDebugger] = None
    
    def _create_default_config(self) -> DebuggerConfig:
        """Create default debugger configuration"""
        config = DebuggerConfig()
        
        # Set appropriate defaults for Xian
        config.debug_level = DebugLevel.STANDARD
        config.monitoring_scope = MonitoringScope.BLOCK
        
        # Enable key monitors
        config.enabled_plugins = [
            'state_tracker',
            'cache_monitor',
            'json_validator',
            'determinism_validator'
        ]
        
        # Configure monitoring thresholds
        config.monitoring.cache_leak_threshold = 50
        config.monitoring.json_failure_threshold = 3
        config.monitoring.state_diff_threshold = 5
        
        # Performance settings
        config.performance.max_memory_mb = 256
        config.performance.max_cpu_percent = 3.0
        
        return config
    
    def initialize(self) -> bool:
        """Initialize the debugger"""
        try:
            self.debugger = initialize_debugger(self.config)
            logger.info("State divergence debugger initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize debugger: {e}")
            return False
    
    def start(self) -> bool:
        """Start the debugger"""
        if not self.debugger:
            if not self.initialize():
                return False
        
        try:
            self.debugger.start()
            logger.info("State divergence debugger started")
            return True
        except Exception as e:
            logger.error(f"Failed to start debugger: {e}")
            return False
    
    def stop(self):
        """Stop the debugger"""
        if self.debugger:
            self.debugger.stop()
            logger.info("State divergence debugger stopped")
    
    def instrument_abci_app(self, abci_app):
        """
        Instrument an ABCI application with debugging hooks.
        
        Args:
            abci_app: The ABCI application instance to instrument
        """
        if not self.debugger:
            logger.warning("Debugger not initialized, skipping instrumentation")
            return abci_app
        
        # Instrument key ABCI methods
        if hasattr(abci_app, 'finalize_block'):
            abci_app.finalize_block = instrument_abci_method('finalize_block')(
                abci_app.finalize_block
            )
        
        if hasattr(abci_app, 'commit'):
            abci_app.commit = instrument_abci_method('commit')(
                abci_app.commit
            )
        
        if hasattr(abci_app, 'check_tx'):
            abci_app.check_tx = instrument_abci_method('check_tx')(
                abci_app.check_tx
            )
        
        logger.info("ABCI application instrumented with debugger hooks")
        return abci_app
    
    def instrument_processor(self, processor):
        """
        Instrument the transaction processor.
        
        Args:
            processor: The transaction processor instance
        """
        if not self.debugger:
            return processor
        
        # Instrument transaction processing methods
        if hasattr(processor, 'process_transaction'):
            processor.process_transaction = instrument_transaction_processing()(
                processor.process_transaction
            )
        
        if hasattr(processor, 'execute_transaction'):
            processor.execute_transaction = instrument_transaction_processing()(
                processor.execute_transaction
            )
        
        logger.info("Transaction processor instrumented with debugger hooks")
        return processor
    
    def instrument_driver(self, driver, driver_name: str = "main"):
        """
        Instrument a driver instance for cache monitoring.
        
        Args:
            driver: The driver instance
            driver_name: Name identifier for the driver
        """
        if not self.debugger:
            return driver
        
        cache_monitor = self.debugger.monitors.get('cache_monitor')
        if cache_monitor:
            # Register the driver's cache for monitoring
            if hasattr(driver, 'cache'):
                cache_monitor.register_cache(f"{driver_name}_cache", driver.cache)
            
            # Instrument cache methods
            if hasattr(driver, 'get'):
                driver.get = instrument_cache_operations(f"{driver_name}_driver")(
                    driver.get
                )
            
            if hasattr(driver, 'set'):
                driver.set = instrument_cache_operations(f"{driver_name}_driver")(
                    driver.set
                )
        
        logger.info(f"Driver '{driver_name}' instrumented with cache monitoring")
        return driver
    
    def get_status(self) -> dict:
        """Get debugger status"""
        if not self.debugger:
            return {'status': 'not_initialized'}
        
        return self.debugger.get_stats()
    
    def get_critical_issues(self) -> list:
        """Get critical issues detected by the debugger"""
        if not self.debugger:
            return []
        
        return self.debugger.get_critical_issues()
    
    def generate_report(self, report_type: str = "summary") -> dict:
        """Generate a debugging report"""
        if not self.debugger:
            return {'error': 'Debugger not initialized'}
        
        return self.debugger.generate_report(report_type)


# Example usage functions

def setup_debugger_for_xian_abci(abci_app, config: Optional[DebuggerConfig] = None):
    """
    Convenience function to set up debugger for Xian ABCI app.
    
    Args:
        abci_app: The ABCI application instance
        config: Optional debugger configuration
    
    Returns:
        DebuggerIntegration: The integration instance
    """
    integration = DebuggerIntegration(config)
    
    if integration.start():
        integration.instrument_abci_app(abci_app)
        return integration
    else:
        logger.error("Failed to start debugger integration")
        return None


def create_debug_context(operation_name: str, **context):
    """
    Create a debug context for manual instrumentation.
    
    Args:
        operation_name: Name of the operation being debugged
        **context: Additional context data
    
    Returns:
        DebuggerContext: Context manager for debugging
    """
    return DebuggerContext(operation_name, **context)


# Example integration with existing Xian code

def example_integration():
    """Example of how to integrate the debugger"""
    
    # 1. Create configuration
    config = DebuggerConfig()
    config.debug_level = DebugLevel.VERBOSE
    config.enabled_plugins = [
        'state_tracker',
        'cache_monitor', 
        'json_validator',
        'determinism_validator'
    ]
    
    # 2. Initialize integration
    integration = DebuggerIntegration(config)
    
    # 3. Start debugger
    if not integration.start():
        logger.error("Failed to start debugger")
        return
    
    try:
        # 4. Your existing ABCI app setup
        # abci_app = XianABCIApp()
        # integration.instrument_abci_app(abci_app)
        
        # 5. Your existing processor setup
        # processor = TxProcessor()
        # integration.instrument_processor(processor)
        
        # 6. Your existing driver setup
        # driver = Driver()
        # integration.instrument_driver(driver, "main_driver")
        
        # 7. Manual instrumentation example
        with create_debug_context("custom_operation", block_height=12345):
            # Your custom code here
            pass
        
        # 8. Check status
        status = integration.get_status()
        logger.info(f"Debugger status: {status}")
        
        # 9. Generate report
        report = integration.generate_report("summary")
        logger.info(f"Debug report: {report}")
        
    finally:
        # 10. Clean shutdown
        integration.stop()


if __name__ == "__main__":
    example_integration()