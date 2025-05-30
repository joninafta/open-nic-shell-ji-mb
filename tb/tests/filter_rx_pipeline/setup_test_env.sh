#!/bin/bash
#
# Filter RX Pipeline Test Environment Setup Script
#
# This script sets up the test environment for the Filter RX Pipeline module.
# It installs required Python packages, sets up the verification environment,
# and validates the installation.
#
# Usage:
#     ./setup_test_env.sh
#     ./setup_test_env.sh --check-only
#     ./setup_test_env.sh --install-cocotb
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}🧪 Filter RX Pipeline Test Environment Setup${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_python() {
    print_info "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d" " -f2)
        print_status "Python 3 found: $PYTHON_VERSION"
        
        # Check if version is >= 3.8
        REQUIRED_VERSION="3.8"
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
            print_status "Python version is compatible (>= 3.8)"
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.8 or later."
        exit 1
    fi
}

check_pip() {
    print_info "Checking pip installation..."
    
    if command -v pip3 &> /dev/null; then
        print_status "pip3 found"
    else
        print_warning "pip3 not found, attempting to install..."
        python3 -m ensurepip --default-pip || {
            print_error "Failed to install pip"
            exit 1
        }
    fi
}

check_virtual_env() {
    print_info "Checking if we're in a virtual environment..."
    
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_status "Virtual environment detected: $VIRTUAL_ENV"
    else
        print_warning "Not in a virtual environment"
        print_info "Consider using a virtual environment:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo ""
        read -p "Continue without virtual environment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

install_requirements() {
    print_info "Installing Python requirements..."
    
    if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
        print_info "Installing from requirements.txt..."
        pip3 install -r "$SCRIPT_DIR/requirements.txt" || {
            print_error "Failed to install requirements"
            exit 1
        }
        print_status "Requirements installed successfully"
    else
        print_warning "requirements.txt not found, installing core packages..."
        pip3 install cocotb scapy pytest || {
            print_error "Failed to install core packages"
            exit 1
        }
    fi
}

check_cocotb() {
    print_info "Checking Cocotb installation..."
    
    if python3 -c "import cocotb" 2>/dev/null; then
        COCOTB_VERSION=$(python3 -c "import cocotb; print(cocotb.__version__)" 2>/dev/null || echo "unknown")
        print_status "Cocotb found: version $COCOTB_VERSION"
        
        # Check if cocotb-config is available
        if command -v cocotb-config &> /dev/null; then
            print_status "cocotb-config command available"
        else
            print_warning "cocotb-config not found in PATH"
            # Try to find it in Python site-packages
            COCOTB_CONFIG=$(python3 -c "import cocotb; import os; print(os.path.join(os.path.dirname(cocotb.__file__), 'cocotb-config'))" 2>/dev/null || echo "")
            if [[ -f "$COCOTB_CONFIG" ]]; then
                print_info "Found cocotb-config at: $COCOTB_CONFIG"
                print_info "Consider adding it to your PATH"
            fi
        fi
        return 0
    else
        print_error "Cocotb not found"
        return 1
    fi
}

check_scapy() {
    print_info "Checking Scapy installation..."
    
    if python3 -c "import scapy" 2>/dev/null; then
        SCAPY_VERSION=$(python3 -c "from scapy import VERSION; print(VERSION)" 2>/dev/null || echo "unknown")
        print_status "Scapy found: version $SCAPY_VERSION"
        return 0
    else
        print_error "Scapy not found"
        return 1
    fi
}

check_simulator() {
    print_info "Checking for HDL simulators..."
    
    SIMULATORS_FOUND=0
    
    # Check for Verilator
    if command -v verilator &> /dev/null; then
        VERILATOR_VERSION=$(verilator --version 2>&1 | head -n1 | awk '{print $2}' 2>/dev/null || echo "unknown")
        print_status "Verilator found: $VERILATOR_VERSION"
        ((SIMULATORS_FOUND++))
    fi
    
    # Check for Questa/ModelSim
    if command -v vsim &> /dev/null; then
        print_status "Questa/ModelSim found"
        ((SIMULATORS_FOUND++))
    fi
    
    # Check for Xcelium
    if command -v xrun &> /dev/null; then
        print_status "Xcelium found"
        ((SIMULATORS_FOUND++))
    fi
    
    # Check for VCS
    if command -v vcs &> /dev/null; then
        print_status "VCS found"
        ((SIMULATORS_FOUND++))
    fi
    
    if [[ $SIMULATORS_FOUND -eq 0 ]]; then
        print_warning "No HDL simulators found"
        print_info "Supported simulators: Verilator, Questa/ModelSim, Xcelium, VCS"
        print_info "For basic testing, Verilator is recommended (free and open source)"
    else
        print_status "$SIMULATORS_FOUND simulator(s) available"
    fi
    
    # Explicitly return success
    return 0
}

validate_test_files() {
    print_info "Validating test files..."
    
    if [[ -f "$SCRIPT_DIR/validate_tests.py" ]]; then
        print_info "Running test validation script..."
        if python3 "$SCRIPT_DIR/validate_tests.py" --run-syntax-check; then
            print_status "Test file validation completed"
        else
            print_error "Test validation failed"
            return 1
        fi
    else
        print_warning "Test validation script not found at $SCRIPT_DIR/validate_tests.py"
    fi
}

run_sample_test() {
    print_info "Running sample syntax check..."
    
    # Check if utils directory exists
    if [[ ! -d "$SCRIPT_DIR/utils" ]]; then
        print_error "Utils directory not found at $SCRIPT_DIR/utils"
        return 1
    fi
    
    # Try to import one of our test modules
    if python3 -c "
import sys
sys.path.append('$SCRIPT_DIR/utils')
try:
    from test_utils import FilterRxTestbench
    print('✅ Test utilities import successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    sys.exit(1)
"; then
        print_status "Sample test passed"
    else
        print_error "Failed to import test utilities"
        return 1
    fi
}

print_summary() {
    echo ""
    print_header
    print_status "Test environment setup completed!"
    echo ""
    print_info "Next steps:"
    echo "  1. Run tests: make test"
    echo "  2. Run specific test suite: make test_basic"
    echo "  3. View all options: make help"
    echo "  4. Validate tests: python3 validate_tests.py"
    echo ""
    print_info "Example commands:"
    echo "  make test_basic              # Run basic functionality tests"
    echo "  make test_all               # Run all test suites"
    echo "  make test SIM=verilator     # Run with specific simulator"
    echo "  make waves                  # View waveforms (after running tests)"
    echo ""
}

# Main execution
main() {
    local check_only=false
    local install_cocotb=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                check_only=true
                shift
                ;;
            --install-cocotb)
                install_cocotb=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --check-only      Only check environment, don't install"
                echo "  --install-cocotb  Force installation of Cocotb and dependencies"
                echo "  -h, --help        Show this help"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    print_header
    
    # Always check environment
    check_python
    check_pip
    
    if [[ "$check_only" != "true" ]]; then
        check_virtual_env
        install_requirements
    fi
    
    # Check installations
    check_cocotb || {
        if [[ "$install_cocotb" == "true" || "$check_only" != "true" ]]; then
            print_info "Cocotb check failed, but continuing..."
        else
            print_error "Cocotb not available. Run with --install-cocotb to install."
            exit 1
        fi
    }
    
    check_scapy || {
        if [[ "$check_only" != "true" ]]; then
            print_info "Scapy check failed, but continuing..."
        fi
    }
    
    check_simulator
    
    if [[ "$check_only" != "true" ]]; then
        if ! validate_test_files; then
            print_error "Test file validation failed"
            exit 1
        fi
        if ! run_sample_test; then
            print_error "Sample test failed"
            exit 1
        fi
        print_summary
    else
        print_status "Check-only mode completed successfully!"
    fi
}

# Run main function with all arguments
main "$@"
