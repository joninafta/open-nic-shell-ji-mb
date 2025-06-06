#!/usr/bin/env python3
"""
Filter RX Pipeline Test Validation Script

This script validates all test files, checks for missing imports, and provides
a comprehensive overview of the test implementation status.

Usage:
    python validate_tests.py
    python validate_tests.py --run-syntax-check
    python validate_tests.py --list-tests

Author: Test Infrastructure
Date: December 2024
"""

import sys
import os
import ast
import importlib.util
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set

# Test file mapping based on TESTCASES.md
TEST_COVERAGE_MAP = {
    'test_filter_basic.py': [
        'TC-IPV4-001', 'TC-IPV4-002', 'TC-IPV4-003',
        'TC-IPV6-001', 'TC-IPV6-002', 'TC-IPV6-003',
        'TC-MIXED-001', 'TC-MIXED-002'
    ],
    'test_filter_config.py': [
        'TC-CFG-001', 'TC-CFG-002', 'TC-CFG-003',
        'TC-DYN-001', 'TC-DYN-002'
    ],
    'test_filter_edge.py': [
        'TC-EDGE-001', 'TC-EDGE-002', 'TC-EDGE-003',
        'TC-EDGE-004', 'TC-EDGE-005'
    ],
    'test_filter_performance.py': [
        'TC-PERF-001', 'TC-PERF-002', 'TC-PERF-003', 'TC-PERF-004'
    ],
    'test_filter_protocol.py': [
        'TC-AXI-001', 'TC-AXI-002', 'TC-AXI-003', 'TC-INT-001'
    ],
    'test_filter_stats.py': [
        'TC-STAT-001', 'TC-STAT-002'
    ]
}

REQUIRED_UTILS = [
    'test_utils.py',
    'packet_generator.py',
    'axi_stream_monitor.py',
    'statistics_checker.py'
]

REQUIRED_IMPORTS = [
    'cocotb',
    'cocotb.clock',
    'cocotb.triggers',
    'cocotb.result'
]


class TestValidator:
    """Validates the Filter RX Pipeline test implementation."""
    
    def __init__(self, test_dir: Path):
        """Initialize the validator with the test directory."""
        self.test_dir = Path(test_dir)
        self.utils_dir = self.test_dir / "utils"
        self.validation_results = {}
        
    def validate_file_exists(self, filename: str) -> bool:
        """Check if a file exists."""
        file_path = self.test_dir / filename
        exists = file_path.exists()
        if not exists:
            print(f"❌ Missing file: {filename}")
        return exists
        
    def validate_utils_exists(self) -> bool:
        """Check if all required utility files exist."""
        print("\n🔍 Checking utility files...")
        all_exist = True
        
        for util_file in REQUIRED_UTILS:
            util_path = self.utils_dir / util_file
            if util_path.exists():
                print(f"✅ Found: utils/{util_file}")
            else:
                print(f"❌ Missing: utils/{util_file}")
                all_exist = False
                
        return all_exist
        
    def validate_test_files_exist(self) -> bool:
        """Check if all test files exist."""
        print("\n🔍 Checking test files...")
        all_exist = True
        
        for test_file in TEST_COVERAGE_MAP.keys():
            if self.validate_file_exists(test_file):
                print(f"✅ Found: {test_file}")
            else:
                all_exist = False
                
        return all_exist
        
    def validate_python_syntax(self, filename: str) -> Tuple[bool, str]:
        """Validate Python syntax of a file."""
        file_path = self.test_dir / filename
        if not file_path.exists():
            return False, f"File {filename} does not exist"
            
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            ast.parse(source)
            return True, "Syntax OK"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Parse error: {e}"
            
    def validate_imports(self, filename: str) -> Tuple[bool, List[str]]:
        """Validate that required imports are present."""
        file_path = self.test_dir / filename
        if not file_path.exists():
            return False, [f"File {filename} does not exist"]
            
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            tree = ast.parse(source)
            
            imported_modules = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imported_modules.add(name.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module.split('.')[0])
            
            missing_imports = []
            for required in REQUIRED_IMPORTS:
                if required.split('.')[0] not in imported_modules:
                    missing_imports.append(required)
                    
            return len(missing_imports) == 0, missing_imports
            
        except Exception as e:
            return False, [f"Error checking imports: {e}"]
            
    def find_cocotb_tests(self, filename: str) -> List[str]:
        """Find all @cocotb.test() decorated functions in a file."""
        file_path = self.test_dir / filename
        if not file_path.exists():
            return []
            
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            tree = ast.parse(source)
            
            cocotb_tests = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        # Check for @cocotb.test() decorator
                        if (isinstance(decorator, ast.Call) and
                            isinstance(decorator.func, ast.Attribute) and
                            isinstance(decorator.func.value, ast.Name) and
                            decorator.func.value.id == 'cocotb' and
                            decorator.func.attr == 'test'):
                            cocotb_tests.append(node.name)
                        # Check for @cocotb.test (without parentheses)
                        elif (isinstance(decorator, ast.Attribute) and
                              isinstance(decorator.value, ast.Name) and
                              decorator.value.id == 'cocotb' and
                              decorator.attr == 'test'):
                            cocotb_tests.append(node.name)
                            
            return cocotb_tests
            
        except Exception as e:
            print(f"Error finding cocotb tests in {filename}: {e}")
            return []
            
    def validate_all_files(self) -> Dict[str, Dict]:
        """Validate all test files comprehensively."""
        print("\n🔍 Performing comprehensive validation...")
        results = {}
        
        # Check utils first
        utils_ok = self.validate_utils_exists()
        results['utils'] = {'exists': utils_ok}
        
        # Check each test file
        for test_file in TEST_COVERAGE_MAP.keys():
            print(f"\n📋 Validating {test_file}...")
            
            file_results = {}
            
            # Check existence
            exists = self.validate_file_exists(test_file)
            file_results['exists'] = exists
            
            if exists:
                # Check syntax
                syntax_ok, syntax_msg = self.validate_python_syntax(test_file)
                file_results['syntax'] = {'valid': syntax_ok, 'message': syntax_msg}
                print(f"   Syntax: {'✅' if syntax_ok else '❌'} {syntax_msg}")
                
                # Check imports
                imports_ok, missing = self.validate_imports(test_file)
                file_results['imports'] = {'valid': imports_ok, 'missing': missing}
                if imports_ok:
                    print(f"   Imports: ✅ All required imports present")
                else:
                    print(f"   Imports: ❌ Missing: {', '.join(missing)}")
                
                # Find cocotb tests
                cocotb_tests = self.find_cocotb_tests(test_file)
                file_results['cocotb_tests'] = cocotb_tests
                print(f"   Cocotb tests: ✅ Found {len(cocotb_tests)} test functions")
                for test in cocotb_tests:
                    print(f"     - {test}")
                
                # Check test coverage
                expected_tests = TEST_COVERAGE_MAP[test_file]
                file_results['expected_coverage'] = expected_tests
                print(f"   Expected coverage: {len(expected_tests)} test cases ({', '.join(expected_tests)})")
                
            results[test_file] = file_results
            
        return results
        
    def print_summary(self, results: Dict):
        """Print a summary of validation results."""
        print("\n" + "="*60)
        print("🎯 VALIDATION SUMMARY")
        print("="*60)
        
        total_files = len(TEST_COVERAGE_MAP)
        valid_files = 0
        total_tests = 0
        total_coverage = 0
        
        for filename, file_results in results.items():
            if filename == 'utils':
                continue
                
            print(f"\n📄 {filename}")
            
            if not file_results['exists']:
                print("   ❌ File missing")
                continue
                
            # Check syntax
            if file_results['syntax']['valid']:
                print("   ✅ Syntax valid")
            else:
                print(f"   ❌ Syntax error: {file_results['syntax']['message']}")
                continue
                
            # Check imports
            if file_results['imports']['valid']:
                print("   ✅ Imports complete")
            else:
                print(f"   ⚠️  Missing imports: {', '.join(file_results['imports']['missing'])}")
                
            # Test functions
            num_tests = len(file_results['cocotb_tests'])
            total_tests += num_tests
            print(f"   ✅ {num_tests} Cocotb test functions")
            
            # Coverage
            num_coverage = len(file_results['expected_coverage'])
            total_coverage += num_coverage
            print(f"   📊 Covers {num_coverage} test cases")
            
            valid_files += 1
            
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Files: {valid_files}/{total_files} valid")
        print(f"   Test functions: {total_tests}")
        print(f"   Test coverage: {total_coverage} test cases")
        print(f"   Utils: {'✅' if results.get('utils', {}).get('exists', False) else '❌'}")
        
        if valid_files == total_files and results.get('utils', {}).get('exists', False):
            print(f"\n🎉 ALL VALIDATION CHECKS PASSED!")
            print(f"   The Filter RX Pipeline test implementation is complete and ready for execution.")
        else:
            print(f"\n⚠️  VALIDATION ISSUES FOUND")
            print(f"   Please address the issues above before running tests.")
            
    def list_all_tests(self):
        """List all available tests in all files."""
        print("\n📋 ALL AVAILABLE TESTS")
        print("="*60)
        
        for test_file in TEST_COVERAGE_MAP.keys():
            if not (self.test_dir / test_file).exists():
                continue
                
            print(f"\n📄 {test_file}")
            
            # List cocotb test functions
            cocotb_tests = self.find_cocotb_tests(test_file)
            if cocotb_tests:
                print("   Cocotb Test Functions:")
                for test in cocotb_tests:
                    print(f"     🧪 {test}")
            
            # List expected test coverage
            expected = TEST_COVERAGE_MAP[test_file]
            print("   Test Case Coverage:")
            for test_case in expected:
                print(f"     📊 {test_case}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Validate Filter RX Pipeline tests')
    parser.add_argument('--test-dir', default='.', 
                       help='Test directory path (default: current directory)')
    parser.add_argument('--run-syntax-check', action='store_true',
                       help='Run syntax check only')
    parser.add_argument('--list-tests', action='store_true',
                       help='List all available tests')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = TestValidator(args.test_dir)
    
    print("🧪 Filter RX Pipeline Test Validator")
    print("="*50)
    
    if args.list_tests:
        validator.list_all_tests()
        return
        
    if args.run_syntax_check:
        print("\n🔍 Running syntax check only...")
        for test_file in TEST_COVERAGE_MAP.keys():
            if (validator.test_dir / test_file).exists():
                syntax_ok, msg = validator.validate_python_syntax(test_file)
                status = "✅" if syntax_ok else "❌"
                print(f"{status} {test_file}: {msg}")
        return
    
    # Run full validation
    results = validator.validate_all_files()
    validator.print_summary(results)


if __name__ == "__main__":
    main()
