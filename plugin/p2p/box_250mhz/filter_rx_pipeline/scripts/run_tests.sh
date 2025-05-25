#!/bin/bash
# Test runner script for filter_rx_pipeline testbench
# Usage: ./run_tests.sh [test_name] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set environment variable for repo root
export OPEN_NIC_SHELL_ROOT="$(cd "$SCRIPT_DIR/../../../../../" && pwd)"

# Build and simulation directories
BUILD_DIR="$OPEN_NIC_SHELL_ROOT/.comp"
SIM_DIR="$OPEN_NIC_SHELL_ROOT/.sim"

# Available tests
AVAILABLE_TESTS=(
    "reset"
    "ipv4_rule_matching"
    "ipv6_rule_matching"
    "port_filtering"
    "counter_verification"
    "pipeline_flow_control"
    "packet_drop_behavior"
    "multi_packet_stream"
    "back_to_back_packets"
    "pipeline_stall_recovery"
    "comprehensive_filtering"
    "performance_stress"
    "regression"  # Special case for all tests
)

# Test descriptions
declare -A TEST_DESCRIPTIONS=(
    ["reset"]="Basic reset and initialization test"
    ["ipv4_rule_matching"]="IPv4 address and port rule matching"
    ["ipv6_rule_matching"]="IPv6 address and port rule matching" 
    ["port_filtering"]="Port-based filtering functionality"
    ["counter_verification"]="Packet counter accuracy verification"
    ["pipeline_flow_control"]="Pipeline ready/valid flow control"
    ["packet_drop_behavior"]="Packet dropping when no rules match"
    ["multi_packet_stream"]="Multiple packet processing"
    ["back_to_back_packets"]="Back-to-back packet handling"
    ["pipeline_stall_recovery"]="Pipeline stall and recovery behavior"
    ["comprehensive_filtering"]="Comprehensive filtering test suite"
    ["performance_stress"]="High-throughput performance testing"
    ["regression"]="Run all tests (full regression suite)"
)

# Function to print colored output
print_status() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_error() {
    echo -e "${RED}[TEST]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [test_name] [options]"
    echo ""
    echo "Available tests:"
    for test in "${AVAILABLE_TESTS[@]}"; do
        echo "  $test - ${TEST_DESCRIPTIONS[$test]}"
    done
    echo ""
    echo "Options:"
    echo "  -v, --verbose    - Enable verbose output"
    echo "  -w, --waves      - Generate waveform files (VCD)"
    echo "  -h, --help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           - Run basic smoke tests"
    echo "  $0 reset                     - Run reset test only"
    echo "  $0 regression                - Run all tests"
    echo "  $0 ipv4_rule_matching -v    - Run IPv4 test with verbose output"
    echo "  $0 performance_stress -w    - Run performance test with waveforms"
}

# Function to check if test name is valid
is_valid_test() {
    local test_name="$1"
    for test in "${AVAILABLE_TESTS[@]}"; do
        if [[ "$test" == "$test_name" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to run a single test
run_single_test() {
    local test_name="$1"
    local verbose="$2"
    local waves="$3"
    
    print_info "Running test: $test_name"
    print_info "Description: ${TEST_DESCRIPTIONS[$test_name]}"
    
    # Check if build exists
    if [[ ! -f "$BUILD_DIR/filter_rx_pipeline/sim" ]]; then
        print_warning "Simulation executable not found. Running build first..."
        if ! ./build.sh; then
            print_error "Build failed"
            return 1
        fi
    fi
    
    # Set environment variables for cocotb
    export TOPLEVEL_LANG=verilog
    export TOPLEVEL=filter_rx_pipeline_tb
    export MODULE=test_filter_rx_pipeline
    export SIM=icarus
    export TESTCASE="test_${test_name}"
    
    # Set optional flags
    if [[ "$waves" == "true" ]]; then
        export WAVES=1
        print_info "Waveform generation enabled"
    fi
    
    if [[ "$verbose" == "true" ]]; then
        export COCOTB_LOG_LEVEL=DEBUG
        print_info "Verbose logging enabled"
    else
        export COCOTB_LOG_LEVEL=INFO
    fi
    
    # Create simulation working directory and ensure it exists
    mkdir -p "$SIM_DIR/filter_rx_pipeline"
    
    # Run the test
    print_status "Executing test: $test_name"
    local start_time=$(date +%s)
    
    # Use cocotb's simple runner approach
    if python3 -c "import cocotb" &> /dev/null; then
        # Create a simple test runner
        BUILD_PATH="$BUILD_DIR/filter_rx_pipeline/sim"
        SIM_PATH="$SIM_DIR/filter_rx_pipeline"
        
        python3 -c "
import os
import sys
import subprocess

# Set up environment
os.environ['TOPLEVEL_LANG'] = 'verilog'
os.environ['TOPLEVEL'] = 'filter_rx_pipeline_tb'
os.environ['MODULE'] = 'test_filter_rx_pipeline'
os.environ['SIM'] = 'icarus'
os.environ['TESTCASE'] = 'test_${test_name}'

# Run cocotb test
try:
    import cocotb
    from cocotb.runner import get_runner
    
    # Simple runner for our test
    result = subprocess.run(['vvp', '${BUILD_PATH}'], 
                          capture_output=False, 
                          cwd='${SIM_PATH}')
    sys.exit(result.returncode)
except ImportError:
    print('cocotb runner not available, using vvp directly')
    result = subprocess.run(['vvp', '${BUILD_PATH}'], 
                          capture_output=False, 
                          cwd='${SIM_PATH}')
    sys.exit(result.returncode)
"
    else
        print_error "cocotb not found. Please install with: pip install cocotb"
        return 1
    fi
    
    local test_result=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Check test result
    if [[ $test_result -eq 0 ]]; then
        print_status "Test $test_name PASSED (${duration}s)"
        return 0
    else
        print_error "Test $test_name FAILED (${duration}s)"
        return 1
    fi
}

# Function to run regression (all tests)
run_regression() {
    local verbose="$1"
    local waves="$2"
    
    print_status "Starting regression test suite"
    
    local passed_tests=()
    local failed_tests=()
    local total_start_time=$(date +%s)
    
    # Run all tests except 'regression' itself
    for test in "${AVAILABLE_TESTS[@]}"; do
        if [[ "$test" != "regression" ]]; then
            print_info "=========================================="
            if run_single_test "$test" "$verbose" "$waves"; then
                passed_tests+=("$test")
            else
                failed_tests+=("$test")
            fi
            echo ""
        fi
    done
    
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    
    # Print summary
    print_info "=========================================="
    print_status "REGRESSION SUMMARY"
    print_info "Total time: ${total_duration}s"
    print_status "Passed tests (${#passed_tests[@]}): ${passed_tests[*]}"
    
    if [[ ${#failed_tests[@]} -gt 0 ]]; then
        print_error "Failed tests (${#failed_tests[@]}): ${failed_tests[*]}"
        return 1
    else
        print_status "All tests passed!"
        return 0
    fi
}

# Parse command line arguments
VERBOSE=false
WAVES=false
TEST_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -w|--waves)
            WAVES=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$TEST_NAME" ]]; then
                TEST_NAME="$1"
            else
                print_error "Multiple test names specified"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# If no test specified, run basic smoke tests
if [[ -z "$TEST_NAME" ]]; then
    print_info "No test specified, running basic smoke tests..."
    SMOKE_TESTS=("reset" "ipv4_rule_matching" "counter_verification")
    
    for test in "${SMOKE_TESTS[@]}"; do
        print_info "=========================================="
        if ! run_single_test "$test" "$VERBOSE" "$WAVES"; then
            print_error "Smoke test failed: $test"
            exit 1
        fi
        echo ""
    done
    
    print_status "All smoke tests passed!"
    exit 0
fi

# Validate test name
if ! is_valid_test "$TEST_NAME"; then
    print_error "Invalid test name: $TEST_NAME"
    echo ""
    echo "Available tests:"
    for test in "${AVAILABLE_TESTS[@]}"; do
        echo "  $test"
    done
    exit 1
fi

# Run the specified test
if [[ "$TEST_NAME" == "regression" ]]; then
    run_regression "$VERBOSE" "$WAVES"
else
    run_single_test "$TEST_NAME" "$VERBOSE" "$WAVES"
fi
