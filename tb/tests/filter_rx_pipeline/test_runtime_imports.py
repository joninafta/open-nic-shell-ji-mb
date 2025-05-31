#!/usr/bin/env python3
"""
Import validation script to test actual runtime imports 
(what CI is testing vs local syntax-only testing)
"""

import sys
import os
from pathlib import Path

def test_actual_imports():
    """Test actual runtime imports for all test files"""
    test_dir = Path(os.getcwd())
    utils_dir = test_dir / "utils"
    
    # Add utils to path
    sys.path.insert(0, str(utils_dir))
    
    print("🧪 Testing Actual Runtime Imports (CI Validation)")
    print("=" * 60)
    
    test_files = [
        'test_filter_basic.py',
        'test_filter_config.py', 
        'test_filter_edge.py',
        'test_filter_performance.py',
        'test_filter_protocol.py',
        'test_filter_stats.py'
    ]
    
    for test_file in test_files:
        print(f"\n📄 Testing imports in {test_file}...")
        
        if not (test_dir / test_file).exists():
            print(f"   ❌ File does not exist")
            continue
            
        try:
            # Try to import the test module
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(
                test_file[:-3], test_dir / test_file
            )
            
            if spec and spec.loader:
                # This is what actually happens during test execution
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # This will fail if imports are missing
                
                print(f"   ✅ All imports successful")
            else:
                print(f"   ❌ Could not create module spec")
                
        except ImportError as e:
            print(f"   ❌ Import error: {e}")
        except AttributeError as e:
            print(f"   ❌ Attribute error (missing class/function): {e}")
        except Exception as e:
            print(f"   ❌ Runtime error: {e}")
    
    # Test utility imports specifically
    print(f"\n📦 Testing utility module imports...")
    
    utils = [
        'test_utils',
        'packet_generator',
        'axi_stream_monitor', 
        'statistics_checker'
    ]
    
    for util in utils:
        try:
            importlib.import_module(util)
            print(f"   ✅ {util}")
        except ImportError as e:
            print(f"   ❌ {util}: {e}")
        except Exception as e:
            print(f"   ❌ {util}: {e}")

if __name__ == "__main__":
    test_actual_imports()
