"""
Debugger Configuration Management

Handles all configuration options for the state divergence debugger.
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


class DebugLevel(Enum):
    """Debug verbosity levels"""
    MINIMAL = "minimal"      # Only critical divergence detection
    STANDARD = "standard"    # Standard monitoring and detection
    VERBOSE = "verbose"      # Detailed logging and analysis
    FORENSIC = "forensic"    # Maximum detail for forensic analysis


class MonitoringScope(Enum):
    """Scope of monitoring operations"""
    TRANSACTION = "transaction"  # Transaction-level monitoring
    BLOCK = "block"             # Block-level monitoring
    FULL_CHAIN = "full_chain"   # Full blockchain monitoring


class StorageMode(Enum):
    """Storage options for debug data"""
    MEMORY = "memory"       # In-memory storage (fastest, limited retention)
    FILE = "file"          # File-based storage
    DATABASE = "database"   # Database storage (most persistent)


@dataclass
class AlertingConfig:
    """Configuration for alerting and notifications"""
    enabled: bool = True
    real_time: bool = True
    batch_interval: int = 300  # seconds
    email_alerts: bool = False
    webhook_url: Optional[str] = None
    alert_threshold: int = 1  # Number of issues before alerting


@dataclass
class PerformanceConfig:
    """Performance and resource usage configuration"""
    max_memory_mb: int = 512
    max_cpu_percent: float = 5.0
    snapshot_retention_hours: int = 24
    max_concurrent_analyses: int = 3
    enable_async_processing: bool = True


@dataclass
class MonitoringConfig:
    """Configuration for different monitoring systems"""
    cache_monitoring: bool = True
    json_validation: bool = True
    state_tracking: bool = True
    determinism_validation: bool = True
    cross_node_comparison: bool = False  # Requires network access
    
    # Specific monitoring thresholds
    cache_leak_threshold: int = 100  # Number of unexpected cache entries
    json_failure_threshold: int = 5   # Number of failures before alert
    state_diff_threshold: int = 10    # Number of state differences before alert


@dataclass
class DebuggerConfig:
    """Main debugger configuration"""
    
    # Core settings
    debug_level: DebugLevel = DebugLevel.STANDARD
    monitoring_scope: MonitoringScope = MonitoringScope.BLOCK
    storage_mode: StorageMode = StorageMode.MEMORY
    enabled: bool = True
    
    # Storage paths
    log_directory: Path = field(default_factory=lambda: Path("./debug_logs"))
    snapshot_directory: Path = field(default_factory=lambda: Path("./debug_snapshots"))
    report_directory: Path = field(default_factory=lambda: Path("./debug_reports"))
    
    # Sub-configurations
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Plugin configuration
    enabled_plugins: List[str] = field(default_factory=lambda: [
        "state_tracker",
        "cache_monitor", 
        "json_validator",
        "determinism_validator",
        "crash_detector"
    ])
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize directories and validate configuration"""
        self._create_directories()
        self._validate_config()
    
    def _create_directories(self):
        """Create necessary directories"""
        for directory in [self.log_directory, self.snapshot_directory, self.report_directory]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self):
        """Validate configuration settings"""
        if self.performance.max_memory_mb < 64:
            raise ValueError("max_memory_mb must be at least 64MB")
        
        if self.performance.max_cpu_percent < 1.0 or self.performance.max_cpu_percent > 50.0:
            raise ValueError("max_cpu_percent must be between 1.0 and 50.0")
        
        if self.performance.snapshot_retention_hours < 1:
            raise ValueError("snapshot_retention_hours must be at least 1")
    
    @classmethod
    def from_env(cls) -> 'DebuggerConfig':
        """Create configuration from environment variables"""
        config = cls()
        
        # Core settings from environment
        if debug_level := os.getenv('XIAN_DEBUG_LEVEL'):
            config.debug_level = DebugLevel(debug_level.lower())
        
        if monitoring_scope := os.getenv('XIAN_MONITORING_SCOPE'):
            config.monitoring_scope = MonitoringScope(monitoring_scope.lower())
        
        if storage_mode := os.getenv('XIAN_STORAGE_MODE'):
            config.storage_mode = StorageMode(storage_mode.lower())
        
        config.enabled = os.getenv('XIAN_DEBUGGER_ENABLED', 'true').lower() == 'true'
        
        # Performance settings
        if max_memory := os.getenv('XIAN_DEBUG_MAX_MEMORY_MB'):
            config.performance.max_memory_mb = int(max_memory)
        
        if max_cpu := os.getenv('XIAN_DEBUG_MAX_CPU_PERCENT'):
            config.performance.max_cpu_percent = float(max_cpu)
        
        # Monitoring settings
        config.monitoring.cache_monitoring = os.getenv('XIAN_CACHE_MONITORING', 'true').lower() == 'true'
        config.monitoring.json_validation = os.getenv('XIAN_JSON_VALIDATION', 'true').lower() == 'true'
        config.monitoring.state_tracking = os.getenv('XIAN_STATE_TRACKING', 'true').lower() == 'true'
        
        # Alerting settings
        config.alerting.enabled = os.getenv('XIAN_ALERTING_ENABLED', 'true').lower() == 'true'
        config.alerting.webhook_url = os.getenv('XIAN_WEBHOOK_URL')
        
        return config
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'DebuggerConfig':
        """Load configuration from JSON file"""
        import json
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Convert string enums back to enum objects
        if 'debug_level' in config_data:
            config_data['debug_level'] = DebugLevel(config_data['debug_level'])
        if 'monitoring_scope' in config_data:
            config_data['monitoring_scope'] = MonitoringScope(config_data['monitoring_scope'])
        if 'storage_mode' in config_data:
            config_data['storage_mode'] = StorageMode(config_data['storage_mode'])
        
        return cls(**config_data)
    
    def to_file(self, config_path: Path):
        """Save configuration to JSON file"""
        import json
        from dataclasses import asdict
        
        config_dict = asdict(self)
        
        # Convert enums to strings for JSON serialization
        config_dict['debug_level'] = self.debug_level.value
        config_dict['monitoring_scope'] = self.monitoring_scope.value
        config_dict['storage_mode'] = self.storage_mode.value
        
        # Convert Path objects to strings
        config_dict['log_directory'] = str(self.log_directory)
        config_dict['snapshot_directory'] = str(self.snapshot_directory)
        config_dict['report_directory'] = str(self.report_directory)
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def is_monitoring_enabled(self, monitor_type: str) -> bool:
        """Check if a specific monitoring type is enabled"""
        return (
            self.enabled and 
            monitor_type in self.enabled_plugins and
            getattr(self.monitoring, f"{monitor_type}_monitoring", True)
        )
    
    def should_alert(self, issue_count: int) -> bool:
        """Determine if an alert should be sent based on issue count"""
        return (
            self.alerting.enabled and 
            issue_count >= self.alerting.alert_threshold
        )