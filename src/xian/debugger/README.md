# Xian State Divergence Debugger

A comprehensive debugging system for detecting and analyzing app hash state divergence issues in the Xian blockchain network.

## Overview

The State Divergence Debugger is designed to help identify, analyze, and resolve issues that can cause nodes in the Xian network to diverge in their state calculations. This includes:

- **Cache Leaks**: Detecting when cache data leaks between transactions or blocks
- **JSON Decode Failures**: Catching silent JSON parsing errors that could cause inconsistent state
- **Non-deterministic Execution**: Identifying contract execution that produces different results across nodes
- **State Corruption**: Detecting unexpected state mutations and inconsistencies
- **Performance Issues**: Monitoring for performance problems that could indicate underlying issues

## Architecture

The debugger follows a plugin-based architecture with the following components:

### Core Components

- **StateDebugger**: Main coordinator that manages all debugging activities
- **EventBus**: Central event system for communication between components
- **PluginManager**: Manages loading and lifecycle of debugger plugins
- **DebuggerConfig**: Configuration management with environment variable support

### Monitor Plugins

- **StateTracker**: Monitors state changes and detects divergence issues
- **CacheMonitor**: Tracks cache usage and detects leaks and pollution
- **JsonValidator**: Validates JSON payloads and detects decode failures
- **DeterminismValidator**: Monitors contract execution for non-deterministic behavior

### Analyzer Plugins

- **DivergenceAnalyzer**: Analyzes state divergence patterns
- **ReplayAnalyzer**: Provides forensic analysis capabilities for replays

### Reporter Plugins

- **LogReporter**: Outputs debugging information to logs
- **FileReporter**: Generates file-based reports
- **WebhookReporter**: Sends alerts via webhooks

## Quick Start

### Basic Integration

```python
from xian.debugger import StateDebugger, DebuggerConfig
from xian.debugger.integration_example import setup_debugger_for_xian_abci

# Create configuration
config = DebuggerConfig()
config.debug_level = DebugLevel.STANDARD
config.enabled_plugins = [
    'state_tracker',
    'cache_monitor',
    'json_validator',
    'determinism_validator'
]

# Set up debugger for your ABCI app
integration = setup_debugger_for_xian_abci(your_abci_app, config)

# The debugger is now monitoring your application
```

### Manual Instrumentation

```python
from xian.debugger.utils.instrumentation import DebuggerContext

# Use context manager for manual instrumentation
with DebuggerContext("custom_operation", block_height=12345):
    # Your code here
    result = process_transaction(tx)
```

### Decorator-based Instrumentation

```python
from xian.debugger.utils.instrumentation import (
    instrument_abci_method,
    instrument_transaction_processing,
    instrument_cache_operations
)

# Instrument ABCI methods
@instrument_abci_method('finalize_block')
def finalize_block(self, request):
    # Your implementation
    pass

# Instrument transaction processing
@instrument_transaction_processing()
def process_transaction(self, tx):
    # Your implementation
    pass

# Instrument cache operations
@instrument_cache_operations('my_cache')
def get_from_cache(self, key):
    # Your implementation
    pass
```

## Configuration

### Environment Variables

```bash
# Core settings
export XIAN_DEBUG_LEVEL=standard
export XIAN_MONITORING_SCOPE=block
export XIAN_DEBUGGER_ENABLED=true

# Performance settings
export XIAN_DEBUG_MAX_MEMORY_MB=256
export XIAN_DEBUG_MAX_CPU_PERCENT=3.0

# Monitoring settings
export XIAN_CACHE_MONITORING=true
export XIAN_JSON_VALIDATION=true
export XIAN_STATE_TRACKING=true

# Alerting settings
export XIAN_ALERTING_ENABLED=true
export XIAN_WEBHOOK_URL=https://your-webhook-url.com/alerts
```

### Configuration File

```python
from xian.debugger.core.config import DebuggerConfig, DebugLevel

config = DebuggerConfig()

# Core settings
config.debug_level = DebugLevel.VERBOSE
config.enabled_plugins = [
    'state_tracker',
    'cache_monitor',
    'json_validator',
    'determinism_validator'
]

# Performance settings
config.performance.max_memory_mb = 512
config.performance.max_cpu_percent = 5.0

# Monitoring thresholds
config.monitoring.cache_leak_threshold = 100
config.monitoring.json_failure_threshold = 5

# Custom settings for specific monitors
config.custom_settings = {
    'state_tracker': {
        'max_snapshots': 1000,
        'divergence_threshold': 3,
        'tracked_keys': ['important_state_key1', 'important_state_key2']
    },
    'cache_monitor': {
        'leak_threshold_multiplier': 2.5,
        'pollution_threshold': 0.2
    }
}
```

## Monitoring Features

### State Tracking

The state tracker monitors:
- State snapshots at block boundaries
- App hash comparisons between nodes
- State key additions/removals/modifications
- Suspicious state change patterns

```python
# Get state tracking information
debugger = get_debugger()
state_tracker = debugger.monitors.get('state_tracker')

# Get recent snapshots
snapshots = state_tracker.get_recent_snapshots(10)

# Add a key to track
state_tracker.add_tracked_key('critical_state_key')

# Get divergence summary
summary = state_tracker.get_divergence_summary()
```

### Cache Monitoring

The cache monitor detects:
- Memory leaks in cache implementations
- Cache pollution (unexpected entries)
- Cleanup failures
- Performance issues

```python
# Register a cache for monitoring
cache_monitor = debugger.monitors.get('cache_monitor')
cache_monitor.register_cache('my_cache', cache_instance)

# Set expected cache patterns
cache_monitor.set_expected_pattern('my_cache', {'expected_key1', 'expected_key2'})

# Get cache statistics
stats = cache_monitor.get_cache_stats()
```

### JSON Validation

The JSON validator catches:
- Silent JSON decode failures
- Payload corruption
- Schema violations
- Suspicious patterns in JSON data

```python
# Set expected schema for validation
json_validator = debugger.monitors.get('json_validator')
json_validator.set_expected_schema('transaction_payload', {
    'required': ['sender', 'contract', 'method'],
    'properties': {
        'sender': 'str',
        'contract': 'str',
        'method': 'str'
    }
})

# Add custom suspicious patterns
json_validator.add_suspicious_pattern(r'\\x[0-9a-fA-F]{2}')

# Get validation statistics
stats = json_validator.get_validation_stats()
```

### Determinism Validation

The determinism validator monitors:
- Non-deterministic function calls (random, time)
- I/O operations during execution
- Result consistency across executions
- Random seed mismatches

```python
# Get determinism statistics
det_validator = debugger.monitors.get('determinism_validator')
stats = det_validator.get_determinism_stats()

# Get analysis for specific contract
analysis = det_validator.get_contract_analysis('my_contract')

# Check random seed consistency
det_validator.check_random_seed_consistency(tx_hash, expected_seed)
```

## Event System

The debugger uses an event-driven architecture. You can subscribe to specific events:

```python
from xian.debugger.core.events import EventType

debugger = get_debugger()

# Subscribe to state divergence events
def handle_divergence(event):
    print(f"State divergence detected: {event.message}")

debugger.event_bus.subscribe(EventType.STATE_DIVERGENCE, handle_divergence)

# Get recent events
recent_events = debugger.get_recent_events(limit=50)
critical_issues = debugger.get_critical_issues()
```

## Reporting

### Generate Reports

```python
# Generate summary report
report = debugger.generate_report("summary")

# Generate detailed report
detailed_report = debugger.generate_report("detailed")

# Get debugger statistics
stats = debugger.get_stats()
```

### Custom Reporters

```python
from xian.debugger.reporters.base import BaseReporter, ReportFormat, ReportType

class CustomReporter(BaseReporter):
    def generate_report(self, report_type, data, format=ReportFormat.JSON):
        # Your custom report generation logic
        pass
    
    def send_notification(self, message, severity="info"):
        # Your custom notification logic
        pass

# Register custom reporter
debugger.register_reporter('custom', CustomReporter(config, event_bus))
```

## Performance Considerations

The debugger is designed to have minimal impact on production performance:

- **Memory Usage**: Configurable limits with automatic cleanup
- **CPU Usage**: Lightweight monitoring with configurable thresholds
- **Async Processing**: Background processing for expensive operations
- **Sampling**: Configurable sampling rates for high-frequency events

### Performance Settings

```python
config.performance.max_memory_mb = 256        # Maximum memory usage
config.performance.max_cpu_percent = 3.0      # Maximum CPU usage
config.performance.enable_async_processing = True
config.performance.max_concurrent_analyses = 2
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Reduce `max_snapshots` in state tracker
   - Decrease `max_tracked_entries` in cache monitor
   - Enable more aggressive cleanup

2. **Performance Impact**
   - Lower `debug_level` to `MINIMAL`
   - Disable non-essential monitors
   - Increase monitoring intervals

3. **Missing Events**
   - Check if debugger is properly initialized and started
   - Verify instrumentation is correctly applied
   - Check event bus subscriptions

### Debug Logging

```python
import logging
logging.getLogger('xian.debugger').setLevel(logging.DEBUG)
```

### Health Checks

```python
# Check if debugger is healthy
debugger = get_debugger()
if debugger:
    stats = debugger.get_stats()
    print(f"Debugger running: {stats['is_running']}")
    print(f"Uptime: {stats['uptime_seconds']} seconds")
    
    # Check monitor health
    for name, monitor in debugger.monitors.items():
        print(f"Monitor {name} healthy: {monitor.is_healthy()}")
```

## Advanced Usage

### Custom Monitors

```python
from xian.debugger.monitors.base import BaseMonitor

class CustomMonitor(BaseMonitor):
    def initialize(self):
        # Initialize your monitor
        return True
    
    def check(self):
        # Perform monitoring check
        pass

# Register custom monitor
debugger.register_monitor('custom', CustomMonitor(config, event_bus))
```

### Replay Analysis

For forensic analysis of state divergence issues:

```python
# This would be implemented in replay_analyzer.py
replay_analyzer = debugger.analyzers.get('replay_analyzer')
if replay_analyzer:
    # Analyze a specific block range
    analysis = replay_analyzer.analyze_block_range(start_height, end_height)
    
    # Compare execution traces
    comparison = replay_analyzer.compare_executions(trace1, trace2)
```

## Integration with Existing Code

### ABCI Integration

The debugger integrates seamlessly with existing ABCI applications:

```python
# In your ABCI app
from xian.debugger.integration_example import setup_debugger_for_xian_abci

class XianABCIApp:
    def __init__(self):
        # Your existing initialization
        
        # Add debugger integration
        self.debugger_integration = setup_debugger_for_xian_abci(self)
    
    def finalize_block(self, request):
        # Your existing implementation
        # Debugger hooks are automatically applied
        pass
```

### Driver Integration

```python
# In your driver code
from xian.debugger.core.debugger import get_debugger

class Driver:
    def __init__(self):
        # Your existing initialization
        
        # Register with debugger
        debugger = get_debugger()
        if debugger:
            cache_monitor = debugger.monitors.get('cache_monitor')
            if cache_monitor:
                cache_monitor.register_cache('driver_cache', self.cache)
```

## Contributing

To add new monitors, analyzers, or reporters:

1. Extend the appropriate base class
2. Implement required methods
3. Register with the plugin manager
4. Add configuration options
5. Write tests

See the existing implementations for examples.

## License

This debugger is part of the Xian blockchain project and follows the same license terms.