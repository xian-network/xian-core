"""
Base Reporter Class

Defines the interface for reporter plugins that handle output and
notification of debugging information.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from ..core.config import DebuggerConfig
from ..core.events import EventBus, DebugEvent


class ReportFormat(Enum):
    """Supported report formats"""
    JSON = "json"
    TEXT = "text"
    HTML = "html"
    CSV = "csv"
    MARKDOWN = "markdown"


class ReportType(Enum):
    """Types of reports"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    CRITICAL_ISSUES = "critical_issues"
    PERFORMANCE = "performance"
    STATE_ANALYSIS = "state_analysis"
    CUSTOM = "custom"


class BaseReporter(ABC):
    """Base class for all reporter plugins"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.name = self.__class__.__name__
        self.is_enabled = True
        
        # Supported formats and types
        self.supported_formats = [ReportFormat.JSON, ReportFormat.TEXT]
        self.supported_types = [ReportType.SUMMARY, ReportType.DETAILED]
        
        # Statistics
        self.stats = {
            'reports_generated': 0,
            'notifications_sent': 0,
            'errors_encountered': 0,
            'last_report_time': None
        }
    
    @abstractmethod
    def generate_report(self, report_type: ReportType, 
                       data: Dict[str, Any],
                       format: ReportFormat = ReportFormat.JSON) -> str:
        """
        Generate a report from the provided data.
        
        Args:
            report_type: Type of report to generate
            data: Data to include in the report
            format: Output format for the report
            
        Returns:
            str: Generated report content
        """
        pass
    
    @abstractmethod
    def send_notification(self, message: str, severity: str = "info") -> bool:
        """
        Send a notification message.
        
        Args:
            message: Message to send
            severity: Severity level (info, warning, error, critical)
            
        Returns:
            bool: True if notification sent successfully
        """
        pass
    
    def can_generate(self, report_type: ReportType, format: ReportFormat) -> bool:
        """
        Check if this reporter can generate the requested report type and format.
        
        Args:
            report_type: Requested report type
            format: Requested format
            
        Returns:
            bool: True if reporter can generate this report
        """
        return (
            self.is_enabled and
            report_type in self.supported_types and
            format in self.supported_formats
        )
    
    def generate_report_safe(self, report_type: ReportType,
                           data: Dict[str, Any],
                           format: ReportFormat = ReportFormat.JSON) -> Optional[str]:
        """
        Generate a report with error handling.
        
        Args:
            report_type: Type of report to generate
            data: Data to include in the report
            format: Output format for the report
            
        Returns:
            Optional[str]: Generated report content or None if failed
        """
        if not self.can_generate(report_type, format):
            return None
        
        try:
            report = self.generate_report(report_type, data, format)
            self.stats['reports_generated'] += 1
            self.stats['last_report_time'] = datetime.now().isoformat()
            return report
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            self.send_notification(
                f"Failed to generate {report_type.value} report: {str(e)}",
                "error"
            )
            return None
    
    def send_notification_safe(self, message: str, severity: str = "info") -> bool:
        """
        Send a notification with error handling.
        
        Args:
            message: Message to send
            severity: Severity level
            
        Returns:
            bool: True if notification sent successfully
        """
        if not self.is_enabled:
            return False
        
        try:
            success = self.send_notification(message, severity)
            if success:
                self.stats['notifications_sent'] += 1
            return success
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            return False
    
    def report_event(self, event: DebugEvent) -> bool:
        """
        Report a debug event.
        
        Args:
            event: Debug event to report
            
        Returns:
            bool: True if reported successfully
        """
        if not self.should_report_event(event):
            return False
        
        # Generate appropriate report based on event
        if event.is_critical():
            report_type = ReportType.CRITICAL_ISSUES
            severity = "critical"
        else:
            report_type = ReportType.SUMMARY
            severity = event.severity.value
        
        # Generate report
        report = self.generate_report_safe(
            report_type,
            {'event': event.to_dict()},
            ReportFormat.TEXT
        )
        
        if report:
            return self.send_notification_safe(report, severity)
        
        return False
    
    def should_report_event(self, event: DebugEvent) -> bool:
        """
        Determine if an event should be reported.
        
        Args:
            event: Debug event to check
            
        Returns:
            bool: True if event should be reported
        """
        if not self.is_enabled:
            return False
        
        # Always report critical events
        if event.is_critical():
            return True
        
        # Check configuration for other events
        return self.config.alerting.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reporter statistics"""
        stats = self.stats.copy()
        stats['name'] = self.name
        stats['is_enabled'] = self.is_enabled
        stats['supported_formats'] = [f.value for f in self.supported_formats]
        stats['supported_types'] = [t.value for t in self.supported_types]
        return stats
    
    def enable(self):
        """Enable the reporter"""
        self.is_enabled = True
    
    def disable(self):
        """Disable the reporter"""
        self.is_enabled = False


class FileReporter(BaseReporter):
    """Base class for file-based reporters"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        self.output_directory = config.report_directory
        self.output_directory.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self, report_type: ReportType, 
                       format: ReportFormat,
                       timestamp: Optional[datetime] = None) -> str:
        """
        Get the output file path for a report.
        
        Args:
            report_type: Type of report
            format: Report format
            timestamp: Optional timestamp for filename
            
        Returns:
            str: Output file path
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type.value}_{timestamp_str}.{format.value}"
        
        return str(self.output_directory / filename)
    
    def write_report_to_file(self, content: str, filepath: str) -> bool:
        """
        Write report content to a file.
        
        Args:
            content: Report content
            filepath: Output file path
            
        Returns:
            bool: True if written successfully
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.stats['errors_encountered'] += 1
            return False


class NetworkReporter(BaseReporter):
    """Base class for network-based reporters (webhooks, APIs, etc.)"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        self.endpoint_url = None
        self.timeout = 30  # seconds
        self.retry_count = 3
    
    def set_endpoint(self, url: str):
        """Set the endpoint URL for network reporting"""
        self.endpoint_url = url
    
    def send_http_request(self, data: Dict[str, Any], 
                         method: str = "POST") -> bool:
        """
        Send HTTP request with report data.
        
        Args:
            data: Data to send
            method: HTTP method
            
        Returns:
            bool: True if request successful
        """
        if not self.endpoint_url:
            return False
        
        import requests
        
        for attempt in range(self.retry_count):
            try:
                response = requests.request(
                    method=method,
                    url=self.endpoint_url,
                    json=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return True
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    self.stats['errors_encountered'] += 1
                    return False
                
                # Wait before retry
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False