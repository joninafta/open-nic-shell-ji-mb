#!/bin/bash
# filepath: /Users/jonafta/Dev/open-nic-shell-ji-mb/tb/tests/filter_rx_pipeline/run_ci_tests.sh
#
# Local CI/CD test runner for Filter RX Pipeline
# Simulates the GitHub Actions workflow locally for development testing

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
TEST_DIR="$SCRIPT_DIR"
RESULTS_DIR="$TEST_DIR/results"
LOG_FILE="$RESULTS_DIR/ci_run.log"

# Default settings
SIM="verilator"
TEST_SUITE="all"
VERBOSE=false
CLEAN=false
PARALLEL=true

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%H:%M:%S')] ${message}${NC}" | tee -a "$LOG_FILE"
}

print_info() { print_status "$BLUE" "INFO: $1"; }
print_success() { print_status "$GREEN" "SUCCESS: $1"; }
print_warning() { print_status "$YELLOW" "WARNING: $1"; }
print_error() { print_status "$RED" "ERROR: $1"; }

# Function to show usage
show_usage() {
    cat << EOF
Filter RX Pipeline CI/CD Test Runner

Usage: $0 [OPTIONS]

Options:
    -s, --simulator SIM     Simulator to use (verilator, questa, xcelium) [default: verilator]
    -t, --test-suite SUITE  Test suite to run (all, basic, config, edge, performance, protocol, stats) [default: all]
    -v, --verbose           Enable verbose output
    -c, --clean             Clean before running tests
    -j, --sequential        Run tests sequentially (not in parallel)
    -h, --help              Show this help message

Examples:
    $0                              # Run all tests with verilator
    $0 -s questa -t basic           # Run basic tests with Questa
    $0 -t performance -v            # Run performance tests with verbose output
    $0 -c -t all                    # Clean and run all tests

Test Suites:
    all         - Complete test suite (all test cases)
    basic       - Basic functionality tests (TC-IPV4, TC-IPV6, TC-MIXED)
    config      - Configuration tests (TC-CFG, TC-DYN)
    edge        - Edge case tests (TC-EDGE)
    performance - Performance tests (TC-PERF)
    protocol    - Protocol compliance tests (TC-AXI, TC-INT)
    stats       - Statistics tests (TC-STAT)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--simulator)
            SIM="$2"
            shift 2
            ;;
        -t|--test-suite)
            TEST_SUITE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -j|--sequential)
            PARALLEL=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate simulator
case $SIM in
    verilator|questa|xcelium)
        ;;
    *)
        print_error "Invalid simulator: $SIM"
        print_info "Valid simulators: verilator, questa, xcelium"
        exit 1
        ;;
esac

# Validate test suite
case $TEST_SUITE in
    all|basic|config|edge|performance|protocol|stats)
        ;;
    *)
        print_error "Invalid test suite: $TEST_SUITE"
        print_info "Valid test suites: all, basic, config, edge, performance, protocol, stats"
        exit 1
        ;;
esac

# Setup results directory
mkdir -p "$RESULTS_DIR"
rm -f "$LOG_FILE"

print_info "Starting Filter RX Pipeline CI/CD Test Run"
print_info "=========================================="
print_info "Project Root: $PROJECT_ROOT"
print_info "Test Directory: $TEST_DIR"
print_info "Simulator: $SIM"
print_info "Test Suite: $TEST_SUITE"
print_info "Results Directory: $RESULTS_DIR"
print_info "Log File: $LOG_FILE"
print_info "=========================================="

# Change to test directory
cd "$TEST_DIR"

# Step 1: Environment validation
print_info "Step 1: Validating test environment..."
if ! ./setup_test_env.sh --check-only >> "$LOG_FILE" 2>&1; then
    print_error "Environment validation failed"
    print_info "Running setup_test_env.sh to fix issues..."
    if ! ./setup_test_env.sh >> "$LOG_FILE" 2>&1; then
        print_error "Environment setup failed. Check $LOG_FILE for details."
        exit 1
    fi
fi
print_success "Environment validation passed"

# Step 2: Test syntax validation
print_info "Step 2: Validating test syntax and completeness..."
if ! python3 validate_tests.py >> "$LOG_FILE" 2>&1; then
    print_error "Test validation failed. Check $LOG_FILE for details."
    exit 1
fi
print_success "Test validation passed"

# Step 3: Clean if requested
if [ "$CLEAN" = true ]; then
    print_info "Step 3: Cleaning previous builds..."
    make clean >> "$LOG_FILE" 2>&1 || true
    rm -rf sim_build/ results/*.xml results/*.log || true
    print_success "Clean completed"
else
    print_info "Step 3: Skipping clean (use -c to clean)"
fi

# Step 4: Set up test environment variables
export COCOTB_REDUCED_LOG_FMT=1
export SIM="$SIM"
if [ "$VERBOSE" = true ]; then
    export COCOTB_LOG_LEVEL=DEBUG
else
    export COCOTB_LOG_LEVEL=INFO
fi

# Step 5: Run tests based on test suite
print_info "Step 4: Running test suite: $TEST_SUITE"
start_time=$(date +%s)

case $TEST_SUITE in
    all)
        if [ "$PARALLEL" = true ]; then
            print_info "Running complete test suite in parallel..."
            if ! make test_all SIM="$SIM" >> "$LOG_FILE" 2>&1; then
                print_error "Test suite failed. Check $LOG_FILE for details."
                exit 1
            fi
        else
            print_info "Running complete test suite sequentially..."
            test_suites=("basic" "config" "edge" "performance" "protocol" "stats")
            for suite in "${test_suites[@]}"; do
                print_info "Running $suite tests..."
                if ! make "test_$suite" SIM="$SIM" >> "$LOG_FILE" 2>&1; then
                    print_error "$suite tests failed. Check $LOG_FILE for details."
                    exit 1
                fi
                print_success "$suite tests passed"
            done
        fi
        ;;
    *)
        print_info "Running $TEST_SUITE tests..."
        if ! make "test_$TEST_SUITE" SIM="$SIM" >> "$LOG_FILE" 2>&1; then
            print_error "$TEST_SUITE tests failed. Check $LOG_FILE for details."
            exit 1
        fi
        ;;
esac

end_time=$(date +%s)
duration=$((end_time - start_time))
print_success "All tests passed! Duration: ${duration}s"

# Step 6: Generate test report
print_info "Step 5: Generating test report..."

report_file="$RESULTS_DIR/ci_test_report.md"
cat > "$report_file" << EOF
# Filter RX Pipeline CI/CD Test Report

**Date:** $(date)
**Simulator:** $SIM
**Test Suite:** $TEST_SUITE
**Duration:** ${duration}s
**Status:** ✅ PASSED

## Environment Information

- **Project Root:** $PROJECT_ROOT
- **Test Directory:** $TEST_DIR
- **Python Version:** $(python3 --version)
- **Simulator Version:** $(which $SIM 2>/dev/null && $SIM --version 2>/dev/null | head -1 || echo "N/A")

## Test Execution Details

EOF

# Add test results if available
if [ -d "results" ]; then
    echo "## Test Results Files" >> "$report_file"
    echo "" >> "$report_file"
    find results -name "*.xml" -o -name "*.log" -o -name "*.txt" | while read -r file; do
        echo "- $file" >> "$report_file"
    done
    echo "" >> "$report_file"
fi

# Add log summary
echo "## Execution Log Summary" >> "$report_file"
echo "" >> "$report_file"
echo '```' >> "$report_file"
tail -50 "$LOG_FILE" >> "$report_file"
echo '```' >> "$report_file"

print_success "Test report generated: $report_file"

# Step 7: Summary
print_info "=========================================="
print_success "CI/CD Test Run Complete!"
print_info "Summary:"
print_info "  - Test Suite: $TEST_SUITE"
print_info "  - Simulator: $SIM"
print_info "  - Duration: ${duration}s"
print_info "  - Status: PASSED"
print_info "  - Report: $report_file"
print_info "  - Log: $LOG_FILE"
print_info "=========================================="

# Optional: Open results if on macOS
if [[ "$OSTYPE" == "darwin"* ]] && command -v open >/dev/null 2>&1; then
    print_info "Opening test report..."
    open "$report_file" 2>/dev/null || true
fi

exit 0
