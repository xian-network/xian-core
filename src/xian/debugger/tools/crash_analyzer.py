#!/usr/bin/env python3
"""
Crash Analysis Tool

Analyzes crash logs and provides insights into what might be causing
the application crashes.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any

def analyze_crash_logs(log_directory: str = "./debug_logs"):
    """Analyze crash logs and provide insights"""
    log_dir = Path(log_directory)
    crash_log_file = log_dir / "crash_log.json"
    
    if not crash_log_file.exists():
        print("No crash log file found. This means either:")
        print("1. No crashes have been detected yet")
        print("2. The debugger hasn't been running")
        print("3. The log directory is different")
        return
    
    crashes = []
    try:
        with open(crash_log_file, 'r') as f:
            for line in f:
                if line.strip():
                    crashes.append(json.loads(line))
    except Exception as e:
        print(f"Error reading crash log: {e}")
        return
    
    if not crashes:
        print("No crashes found in log file")
        return
    
    print(f"\n🔍 CRASH ANALYSIS REPORT")
    print(f"=" * 50)
    print(f"Total crashes detected: {len(crashes)}")
    print(f"Analysis period: {crashes[0]['timestamp']} to {crashes[-1]['timestamp']}")
    
    # Analyze crash types
    crash_types = Counter(crash['type'] for crash in crashes)
    print(f"\n📊 Crash Types:")
    for crash_type, count in crash_types.items():
        print(f"  {crash_type}: {count}")
    
    # Analyze crash locations/methods
    methods = []
    for crash in crashes:
        if 'recent_operations' in crash:
            for op in crash['recent_operations'][-3:]:  # Last 3 operations
                if 'operation' in op:
                    methods.append(op['operation'])
    
    if methods:
        method_counts = Counter(methods)
        print(f"\n🎯 Most Common Operations Before Crashes:")
        for method, count in method_counts.most_common(5):
            print(f"  {method}: {count}")
    
    # Analyze exception types
    exception_types = []
    for crash in crashes:
        if crash['type'] == 'exception' and 'exception_type' in crash:
            exception_types.append(crash['exception_type'])
    
    if exception_types:
        exc_counts = Counter(exception_types)
        print(f"\n⚠️  Exception Types:")
        for exc_type, count in exc_counts.items():
            print(f"  {exc_type}: {count}")
    
    # Show recent crashes with details
    print(f"\n🕐 Recent Crashes (last 3):")
    for crash in crashes[-3:]:
        print(f"\n  Time: {crash['timestamp']}")
        print(f"  Type: {crash['type']}")
        
        if crash['type'] == 'exception':
            print(f"  Exception: {crash.get('exception_type', 'Unknown')}")
            print(f"  Message: {crash.get('exception_message', 'No message')}")
        elif crash['type'] == 'signal':
            print(f"  Signal: {crash.get('signal', 'Unknown')}")
        
        if 'recent_operations' in crash and crash['recent_operations']:
            print(f"  Last operations:")
            for op in crash['recent_operations'][-3:]:
                print(f"    - {op.get('operation', 'Unknown')}")
    
    # Provide recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if 'SyntaxWarning' in str(crashes):
        print("  • Fix syntax warnings in contract code (found 'is' with literal)")
    
    if any('memory' in str(crash).lower() for crash in crashes):
        print("  • Check for memory leaks in contract execution")
    
    if any('json' in str(crash).lower() for crash in crashes):
        print("  • Validate JSON parsing in contract state")
    
    if len(crashes) > 5:
        print("  • Consider running with reduced load to isolate the issue")
        print("  • Check system resources (memory, disk space)")
    
    print("  • Review the contract code that was being processed when crashes occurred")
    print("  • Consider adding more specific error handling in contract execution")

def main():
    """Main entry point"""
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "./debug_logs"
    analyze_crash_logs(log_dir)

if __name__ == "__main__":
    main()