#!/bin/bash
# Build script for filter_rx_pipeline testbench
# Usage: ./build.sh [clean]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set environment variable for repo root
export OPEN_NIC_SHELL_ROOT="$(cd "$SCRIPT_DIR/../../../../../" && pwd)"

# Build and simulation directories
BUILD_DIR="$OPEN_NIC_SHELL_ROOT/.comp"
SIM_DIR="$OPEN_NIC_SHELL_ROOT/.sim"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[BUILD]${NC} $1"
}

print_error() {
    echo -e "${RED}[BUILD]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [clean]"
    echo "  clean    - Clean build artifacts before building"
    echo ""
    echo "Examples:"
    echo "  $0        - Build the testbench"
    echo "  $0 clean - Clean and build the testbench"
}

# Handle command line arguments
if [[ $# -gt 1 ]]; then
    show_usage
    exit 1
fi

if [[ $# -eq 1 ]]; then
    case "$1" in
        clean)
            print_status "Cleaning build artifacts..."
            rm -rf "$BUILD_DIR/filter_rx_pipeline"
            rm -rf "$SIM_DIR/filter_rx_pipeline"
            rm -rf sim_build/
            rm -rf __pycache__/
            rm -rf .pytest_cache/
            rm -f results.xml
            rm -f *.vcd
            rm -f *.fst
            rm -f *.log
            rm -f *.lxt
            rm -f dump.vcd
            rm -f *.out
            print_status "Clean complete"
            ;;
        -h|--help|help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
fi

# Check for required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

print_status "Checking required tools..."
check_tool "verilator"

# Verilog source files
VERILOG_SOURCES=(
    "../src/filter_rx_pipeline.sv"
    "../tb/filter_rx_pipeline_tb.sv"
    "../../../../../src/utility/axi_stream_register_slice.sv"
)

# Check if all source files exist
print_status "Checking source files..."
for file in "${VERILOG_SOURCES[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_error "Source file not found: $file"
        exit 1
    fi
done

# Package files
PACKAGE_FILES=(
    "../../common/cfg_reg_pkg.sv"
    "../../common/packet_pkg.sv"
)

# Check package files
for file in "${PACKAGE_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_error "Package file not found: $file"
        exit 1
    fi
done

# Build the testbench
print_status "Building testbench..."

# Create build and simulation directories if they don't exist
mkdir -p "$BUILD_DIR/filter_rx_pipeline"
mkdir -p "$SIM_DIR/filter_rx_pipeline"

# Create local sim_build directory for compatibility
mkdir -p sim_build

# Verilator compilation
verilator --lint-only --sv \
    -Wno-TIMESCALEMOD \
    -Wno-WIDTHEXPAND \
    -I../../../../../src \
    -I../../common \
    -I../src \
    --top-module filter_rx_pipeline_tb \
    ${PACKAGE_FILES[@]} \
    ${VERILOG_SOURCES[@]}

verilator_result=$?

if [ $verilator_result -eq 0 ]; then
    # Create a simulation executable that works with the unified test runner
    cat > "$BUILD_DIR/filter_rx_pipeline/sim" << 'EOF'
#!/bin/bash
# Filter RX Pipeline Simulation Executable
# This calls our unified Python test runner

# Get the script directory (where run_tests.py is located)
SCRIPTS_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")/../../../plugin/p2p/box_250mhz/filter_rx_pipeline/scripts"

# Execute the unified Python test runner
python3 "$SCRIPTS_DIR/run_tests.py" "$@"
EOF
    chmod +x "$BUILD_DIR/filter_rx_pipeline/sim"
    
    print_status "Build completed successfully!"
    print_status "Build output: $BUILD_DIR/filter_rx_pipeline/sim"
    print_status "Use ./run_tests.py to run tests"
else
    print_error "Verilator compilation failed with code $verilator_result"
    exit 1
fi
