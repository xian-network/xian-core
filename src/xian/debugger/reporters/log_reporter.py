"""
Log Reporter

Simple reporter that outputs debugging information to logs.
"""

import json
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from .base import BaseReporter, ReportFormat, ReportType
from ..core.config import DebuggerConfig
from ..core.events import EventBus, DebugEvent


class LogReporter(BaseReporter):
    """Reporter that outputs to logs"""
    
    def __init__(self, config: DebuggerConfig, event_bus: EventBus):
        super().__init__(config, event_bus)
        
        # Support all basic formats
        self.supported_formats = [
            ReportFormat.JSON,
            ReportFormat.TEXT,
            ReportFormat.MARKDOWN
        ]
        
        # Support all report types
        self.supported_types = [
            ReportType.SUMMARY,
            ReportType.DETAILED,
            ReportType.CRITICAL_ISSUES,
            ReportType.PERFORMANCE
        ]
    
    def generate_report(self, report_type: ReportType, 
                       data: Dict[str, Any],
                       format: ReportFormat = ReportFormat.JSON) -> str:
        """Generate a report in the specified format"""
        
        if format == ReportFormat.JSON:
            return self._generate_json_report(report_type, data)
        elif format == ReportFormat.TEXT:
            return self._generate_text_report(report_type, data)
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(report_type, data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def send_notification(self, message: str, severity: str = "info") -> bool:
        """Send notification via logging"""
        try:
            if severity == "critical":
                logger.critical(f"[DEBUGGER] {message}")
            elif severity == "error":
                logger.error(f"[DEBUGGER] {message}")
            elif severity == "warning":
                logger.warning(f"[DEBUGGER] {message}")
            else:
                logger.info(f"[DEBUGGER] {message}")
            
            return True
        except Exception:
            return False
    
    def _generate_json_report(self, report_type: ReportType, data: Dict[str, Any]) -> str:
        """Generate JSON format report"""
        report = {
            'report_type': report_type.value,
            'generated_at': datetime.now().isoformat(),
            'data': data
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def _generate_text_report(self, report_type: ReportType, data: Dict[str, Any]) -> str:
        """Generate text format report"""
        lines = [
            f"=== {report_type.value.upper()} REPORT ===",
            f"Generated at: {datetime.now().isoformat()}",
            ""
        ]
        
        if report_type == ReportType.SUMMARY:
            lines.extend(self._format_summary_text(data))
        elif report_type == ReportType.CRITICAL_ISSUES:
            lines.extend(self._format_critical_issues_text(data))
        elif report_type == ReportType.PERFORMANCE:
            lines.extend(self._format_performance_text(data))
        else:
            lines.extend(self._format_generic_text(data))
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, report_type: ReportType, data: Dict[str, Any]) -> str:
        """Generate markdown format report"""
        lines = [
            f"# {report_type.value.title()} Report",
            f"**Generated at:** {datetime.now().isoformat()}",
            ""
        ]
        
        if report_type == ReportType.SUMMARY:
            lines.extend(self._format_summary_markdown(data))
        elif report_type == ReportType.CRITICAL_ISSUES:
            lines.extend(self._format_critical_issues_markdown(data))
        else:
            lines.extend(self._format_generic_markdown(data))
        
        return "\n".join(lines)
    
    def _format_summary_text(self, data: Dict[str, Any]) -> list:
        """Format summary data as text"""
        lines = []
        
        if 'stats' in data:
            stats = data['stats']
            lines.extend([
                "DEBUGGER STATISTICS:",
                f"  Running: {stats.get('is_running', False)}",
                f"  Uptime: {stats.get('uptime_seconds', 0):.1f} seconds",
                f"  Events Processed: {stats.get('stats', {}).get('events_processed', 0)}",
                f"  Divergences Detected: {stats.get('stats', {}).get('divergences_detected', 0)}",
                f"  Cache Leaks Found: {stats.get('stats', {}).get('cache_leaks_found', 0)}",
                f"  JSON Errors Caught: {stats.get('stats', {}).get('json_errors_caught', 0)}",
                ""
            ])
        
        if 'critical_issues' in data:
            issues = data['critical_issues']
            lines.extend([
                f"CRITICAL ISSUES: {len(issues)}",
                ""
            ])
            
            for issue in issues[:5]:  # Show first 5
                lines.append(f"  - {issue.get('message', 'Unknown issue')}")
            
            if len(issues) > 5:
                lines.append(f"  ... and {len(issues) - 5} more")
        
        return lines
    
    def _format_critical_issues_text(self, data: Dict[str, Any]) -> list:
        """Format critical issues as text"""
        lines = []
        
        if 'event' in data:
            event = data['event']
            lines.extend([
                f"EVENT: {event.get('event_type', 'unknown')}",
                f"SEVERITY: {event.get('severity', 'unknown')}",
                f"MESSAGE: {event.get('message', 'No message')}",
                f"TIMESTAMP: {event.get('timestamp', 'unknown')}",
                ""
            ])
            
            if event.get('block_height'):
                lines.append(f"Block Height: {event['block_height']}")
            
            if event.get('transaction_hash'):
                lines.append(f"Transaction: {event['transaction_hash']}")
            
            if event.get('data'):
                lines.extend([
                    "",
                    "EVENT DATA:",
                    json.dumps(event['data'], indent=2, default=str)
                ])
        
        return lines
    
    def _format_performance_text(self, data: Dict[str, Any]) -> list:
        """Format performance data as text"""
        lines = []
        
        if 'stats' in data:
            stats = data['stats']
            lines.extend([
                "PERFORMANCE METRICS:",
                f"  Performance Warnings: {stats.get('stats', {}).get('performance_warnings', 0)}",
                ""
            ])
        
        return lines
    
    def _format_generic_text(self, data: Dict[str, Any]) -> list:
        """Format generic data as text"""
        return [json.dumps(data, indent=2, default=str)]
    
    def _format_summary_markdown(self, data: Dict[str, Any]) -> list:
        """Format summary data as markdown"""
        lines = []
        
        if 'stats' in data:
            stats = data['stats']
            lines.extend([
                "## Debugger Statistics",
                "",
                f"- **Running:** {stats.get('is_running', False)}",
                f"- **Uptime:** {stats.get('uptime_seconds', 0):.1f} seconds",
                f"- **Events Processed:** {stats.get('stats', {}).get('events_processed', 0)}",
                f"- **Divergences Detected:** {stats.get('stats', {}).get('divergences_detected', 0)}",
                f"- **Cache Leaks Found:** {stats.get('stats', {}).get('cache_leaks_found', 0)}",
                f"- **JSON Errors Caught:** {stats.get('stats', {}).get('json_errors_caught', 0)}",
                ""
            ])
        
        if 'critical_issues' in data:
            issues = data['critical_issues']
            lines.extend([
                f"## Critical Issues ({len(issues)})",
                ""
            ])
            
            for i, issue in enumerate(issues[:10], 1):
                lines.append(f"{i}. {issue.get('message', 'Unknown issue')}")
            
            if len(issues) > 10:
                lines.append(f"... and {len(issues) - 10} more")
        
        return lines
    
    def _format_critical_issues_markdown(self, data: Dict[str, Any]) -> list:
        """Format critical issues as markdown"""
        lines = []
        
        if 'event' in data:
            event = data['event']
            lines.extend([
                "## Event Details",
                "",
                f"- **Type:** {event.get('event_type', 'unknown')}",
                f"- **Severity:** {event.get('severity', 'unknown')}",
                f"- **Timestamp:** {event.get('timestamp', 'unknown')}",
                ""
            ])
            
            if event.get('block_height'):
                lines.append(f"- **Block Height:** {event['block_height']}")
            
            if event.get('transaction_hash'):
                lines.append(f"- **Transaction:** {event['transaction_hash']}")
            
            lines.extend([
                "",
                f"### Message",
                event.get('message', 'No message'),
                ""
            ])
            
            if event.get('data'):
                lines.extend([
                    "### Event Data",
                    "```json",
                    json.dumps(event['data'], indent=2, default=str),
                    "```"
                ])
        
        return lines
    
    def _format_generic_markdown(self, data: Dict[str, Any]) -> list:
        """Format generic data as markdown"""
        return [
            "## Data",
            "```json",
            json.dumps(data, indent=2, default=str),
            "```"
        ]