#!/usr/bin/env python3
"""
Startup Diagnostic Tool

Runs diagnostic checks before starting the application to identify
potential issues that could cause crashes.
"""

import os
import sys
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"  ❌ Python {version.major}.{version.minor} detected. Python 3.8+ required.")
        return False
    else:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True

def check_dependencies():
    """Check required dependencies"""
    print("\n📦 Checking dependencies...")
    required_deps = [
        'loguru',
        'psutil',
        'asyncio'
    ]
    
    missing_deps = []
    for dep in required_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep} - OK")
        except ImportError:
            print(f"  ❌ {dep} - MISSING")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n  Install missing dependencies with:")
        print(f"  pip install {' '.join(missing_deps)}")
        return False
    
    return True

def check_file_permissions():
    """Check file system permissions"""
    print("\n📁 Checking file permissions...")
    
    # Check current directory write permissions
    try:
        test_file = Path("./test_write_permission.tmp")
        test_file.write_text("test")
        test_file.unlink()
        print("  ✅ Current directory - writable")
    except Exception as e:
        print(f"  ❌ Current directory - not writable: {e}")
        return False
    
    # Check debug directories
    debug_dirs = ["./debug_logs", "./debug_snapshots", "./debug_reports"]
    for dir_path in debug_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            test_file = Path(dir_path) / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print(f"  ✅ {dir_path} - writable")
        except Exception as e:
            print(f"  ❌ {dir_path} - not writable: {e}")
            return False
    
    return True

def check_memory_resources():
    """Check available memory"""
    print("\n💾 Checking memory resources...")
    try:
        import psutil
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        if available_gb < 1.0:
            print(f"  ⚠️  Low memory: {available_gb:.1f}GB available")
            print("     Consider freeing up memory before running")
        else:
            print(f"  ✅ Memory: {available_gb:.1f}GB available")
        
        return available_gb > 0.5  # At least 500MB
        
    except ImportError:
        print("  ⚠️  psutil not available - cannot check memory")
        return True
    except Exception as e:
        print(f"  ❌ Memory check failed: {e}")
        return False

def check_contract_syntax():
    """Check for common contract syntax issues"""
    print("\n📝 Checking for common syntax issues...")
    
    # Look for Python files that might contain contracts
    python_files = []
    for root, dirs, files in os.walk("."):
        # Skip hidden directories and common non-contract directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                python_files.append(Path(root) / file)
    
    issues_found = 0
    for py_file in python_files[:50]:  # Limit to first 50 files
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            # Check for common issues
            if ' is "' in content or " is '" in content:
                print(f"  ⚠️  {py_file}: Found 'is' with string literal (use == instead)")
                issues_found += 1
            
            if ' is 0' in content or ' is 1' in content:
                print(f"  ⚠️  {py_file}: Found 'is' with numeric literal (use == instead)")
                issues_found += 1
                
        except Exception as e:
            # Skip files we can't read
            continue
    
    if issues_found == 0:
        print("  ✅ No obvious syntax issues found")
    else:
        print(f"  ⚠️  Found {issues_found} potential syntax issues")
    
    return issues_found < 10  # Allow some issues but not too many

def check_debugger_config():
    """Check debugger configuration"""
    print("\n🔧 Checking debugger configuration...")
    
    try:
        # Try to import and initialize config
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.config import DebuggerConfig
        
        config = DebuggerConfig()
        print(f"  ✅ Debugger enabled: {config.enabled}")
        print(f"  ✅ Log directory: {config.log_directory}")
        print(f"  ✅ Enabled plugins: {len(config.enabled_plugins)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Debugger config error: {e}")
        traceback.print_exc()
        return False

def run_diagnostics():
    """Run all diagnostic checks"""
    print("🔍 XIAN STARTUP DIAGNOSTICS")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("File Permissions", check_file_permissions),
        ("Memory Resources", check_memory_resources),
        ("Contract Syntax", check_contract_syntax),
        ("Debugger Config", check_debugger_config)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"  ❌ {check_name} check failed with error: {e}")
    
    print(f"\n📊 DIAGNOSTIC SUMMARY")
    print(f"=" * 40)
    print(f"Passed: {passed}/{total} checks")
    
    if passed == total:
        print("🎉 All checks passed! Your system looks ready to run.")
        return True
    elif passed >= total - 2:
        print("⚠️  Most checks passed. You can probably run, but watch for issues.")
        return True
    else:
        print("❌ Several issues detected. Fix these before running to avoid crashes.")
        return False

def main():
    """Main entry point"""
    success = run_diagnostics()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()