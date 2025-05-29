# Makefile for filter_rx_pipeline Cocotb testbench
# OpenNIC Shell Verification Environment

# Project settings
PROJECT_ROOT := $(shell cd ../../.. && pwd)
TB_ROOT = $(PROJECT_ROOT)/tb
MODULE_NAME = filter_rx_pipeline

# Simulator settings
SIM ?= verilator
TOPLEVEL_LANG ?= verilog
TOPLEVEL = tb_$(MODULE_NAME)

# Source files
VERILOG_SOURCES = $(PROJECT_ROOT)/plugin/p2p/box_250mhz/common/cfg_reg_pkg.sv
VERILOG_SOURCES += $(PROJECT_ROOT)/plugin/p2p/box_250mhz/common/packet_pkg.sv
VERILOG_SOURCES += $(PROJECT_ROOT)/plugin/p2p/box_250mhz/$(MODULE_NAME)/src/$(MODULE_NAME).sv
VERILOG_SOURCES += tb_$(MODULE_NAME).sv

# Include directories
COMPILE_ARGS += +incdir+$(PROJECT_ROOT)/src
COMPILE_ARGS += +incdir+$(PROJECT_ROOT)/plugin/p2p/box_250mhz/$(MODULE_NAME)/src
COMPILE_ARGS += +incdir+$(PROJECT_ROOT)/plugin/p2p/box_250mhz/common

# Simulator specific options
ifeq ($(SIM),questa)
    COMPILE_ARGS += +acc
    COMPILE_ARGS += -timescale 1ns/1ps
    COMPILE_ARGS += -sv
endif

ifeq ($(SIM),xcelium)
    COMPILE_ARGS += -access +rwc
    COMPILE_ARGS += -timescale 1ns/1ps
    COMPILE_ARGS += -sv
endif

ifeq ($(SIM),vcs)
    COMPILE_ARGS += +acc+1
    COMPILE_ARGS += -timescale=1ns/1ps
    COMPILE_ARGS += -sverilog
endif

ifeq ($(SIM),verilator)
    COMPILE_ARGS += --binary
    COMPILE_ARGS += --trace
    COMPILE_ARGS += --trace-structs
    COMPILE_ARGS += --timing
    COMPILE_ARGS += -Wno-UNUSEDSIGNAL
    COMPILE_ARGS += -Wno-UNUSEDPARAM
    COMPILE_ARGS += -Wno-GENUNNAMED
    COMPILE_ARGS += -Wno-IMPORTSTAR
    COMPILE_ARGS += -Wno-VARHIDDEN
    COMPILE_ARGS += --coverage
    COMPILE_ARGS += --x-assign unique
    COMPILE_ARGS += --x-initial unique
endif

# Test modules (Python)
MODULE ?= test_filter_basic

# Python path setup - ensure tb package is importable
PYTHONPATH := $(PROJECT_ROOT):$(PYTHONPATH)
export PYTHONPATH

# Test targets
.PHONY: test waves help

# Default test
test: test_basic

# Individual test suites
test_basic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_basic_comprehensive

test_config:
	$(MAKE) run MODULE=test_filter_config TESTCASE=test_config_comprehensive

test_edge:
	$(MAKE) run MODULE=test_filter_edge TESTCASE=test_edge_comprehensive

test_performance:
	$(MAKE) run MODULE=test_filter_performance TESTCASE=test_performance_comprehensive

test_protocol:
	$(MAKE) run MODULE=test_filter_protocol TESTCASE=test_protocol_comprehensive

test_stats:
	$(MAKE) run MODULE=test_filter_stats TESTCASE=test_statistics_comprehensive

# Individual test cases for basic functionality
test_ipv4_basic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_ipv4_basic_filtering

test_ipv6_basic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_ipv6_basic_filtering

test_mixed_traffic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_mixed_traffic_filtering

# Individual test cases for configuration
test_rule_config:
	$(MAKE) run MODULE=test_filter_config TESTCASE=test_rule_configuration

test_dynamic_reconfig:
	$(MAKE) run MODULE=test_filter_config TESTCASE=test_dynamic_reconfiguration

# Individual test cases for edge cases
test_malformed:
	$(MAKE) run MODULE=test_filter_edge TESTCASE=test_malformed_packets

test_backpressure:
	$(MAKE) run MODULE=test_filter_edge TESTCASE=test_backpressure_handling

# Individual test cases for performance
test_throughput:
	$(MAKE) run MODULE=test_filter_performance TESTCASE=test_maximum_throughput

test_burst:
	$(MAKE) run MODULE=test_filter_performance TESTCASE=test_burst_traffic

# Individual test cases for protocol compliance
test_axi_compliance:
	$(MAKE) run MODULE=test_filter_protocol TESTCASE=test_axi_stream_compliance

test_packet_integrity:
	$(MAKE) run MODULE=test_filter_protocol TESTCASE=test_packet_integrity

# Individual test cases for statistics
test_counter_accuracy:
	$(MAKE) run MODULE=test_filter_stats TESTCASE=test_statistics_counters

test_counter_overflow:
	$(MAKE) run MODULE=test_filter_stats TESTCASE=test_counter_overflow

# Run all comprehensive test suites
test_all:
	@echo "Running all comprehensive test suites..."
	$(MAKE) test_basic
	$(MAKE) test_config
	$(MAKE) test_edge
	$(MAKE) test_performance
	$(MAKE) test_protocol
	$(MAKE) test_stats

# Run functional tests only (faster subset)
test_functional:
	@echo "Running functional tests..."
	$(MAKE) test_basic
	$(MAKE) test_config

# Run compliance tests only
test_compliance:
	@echo "Running compliance tests..."
	$(MAKE) test_protocol
	$(MAKE) test_stats

# Run performance tests only
test_perf:
	@echo "Running performance tests..."
	$(MAKE) test_performance

# Internal run target
run:
	@echo "Running $(MODULE).$(TESTCASE) with $(SIM)"
	@echo "Project root: $(PROJECT_ROOT)"
	@echo "Python path: $(PYTHONPATH)"
	$(MAKE) sim

# View waveforms
waves:
	@if [ -f "$(MODULE_NAME).vcd" ]; then \
		gtkwave $(MODULE_NAME).vcd; \
	elif [ -f "waves.shm" ]; then \
		simvision waves.shm; \
	elif [ -f "vsim.wlf" ]; then \
		vsim -view vsim.wlf; \
	else \
		echo "No waveform files found"; \
	fi

# Help target
help:
	@echo "OpenNIC Filter RX Pipeline Comprehensive Testbench"
	@echo ""
	@echo "Available test suites:"
	@echo "  test              - Run basic functionality test (default)"
	@echo "  test_all          - Run all comprehensive test suites"
	@echo "  test_functional   - Run functional tests only (basic + config)"
	@echo "  test_compliance   - Run compliance tests only (protocol + stats)"
	@echo "  test_perf         - Run performance tests only"
	@echo ""
	@echo "Individual test suites:"
	@echo "  test_basic        - Basic filtering functionality (TC-IPV4-*, TC-IPV6-*, TC-MIXED-*)"
	@echo "  test_config       - Configuration and dynamic tests (TC-CFG-*, TC-DYN-*)"
	@echo "  test_edge         - Edge cases and error handling (TC-EDGE-*)"
	@echo "  test_performance  - Performance and throughput tests (TC-PERF-*)"
	@echo "  test_protocol     - Protocol compliance tests (TC-AXI-*, TC-INT-*)"
	@echo "  test_stats        - Statistics verification tests (TC-STAT-*)"
	@echo ""
	@echo "Individual test cases:"
	@echo "  test_ipv4_basic      - Basic IPv4 filtering"
	@echo "  test_ipv6_basic      - Basic IPv6 filtering"
	@echo "  test_mixed_traffic   - Mixed IPv4/IPv6 traffic"
	@echo "  test_rule_config     - Rule configuration"
	@echo "  test_dynamic_reconfig - Dynamic reconfiguration"
	@echo "  test_malformed       - Malformed packet handling"
	@echo "  test_backpressure    - Back-pressure handling"
	@echo "  test_throughput      - Maximum throughput test"
	@echo "  test_burst           - Burst traffic test"
	@echo "  test_axi_compliance  - AXI Stream compliance"
	@echo "  test_packet_integrity - Packet data integrity"
	@echo "  test_counter_accuracy - Counter accuracy"
	@echo "  test_counter_overflow - Counter overflow behavior"
	@echo ""
	@echo "Utilities:"
	@echo "  waves         - View waveforms"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Environment variables:"
	@echo "  SIM           - Simulator (verilator, questa, xcelium, vcs) [default: verilator]"
	@echo "  PROJECT_ROOT  - Project root directory [default: ../../../..]"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Run basic test with default simulator (Verilator)"
	@echo "  make test_all SIM=questa     # Run all tests with Questa"
	@echo "  make test_functional         # Run functional tests only"
	@echo "  make test_performance        # Run performance tests"
	@echo "  make test_ipv4_basic         # Run specific IPv4 test"
	@echo "  make waves                   # View waveforms"

# Include Cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
