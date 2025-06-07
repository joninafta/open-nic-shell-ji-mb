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

# Source files - include packages first, then modules
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
    COMPILE_ARGS += -CFLAGS -std=c++14
    COMPILE_ARGS += -LDFLAGS -std=c++14
    COMPILE_ARGS += --language 1800-2012
    COMPILE_ARGS += -Wno-fatal
endif

# Test modules (Python)
MODULE ?= test_filter_basic

# Python path setup - ensure tb package is importable
PYTHONPATH := $(PROJECT_ROOT):$(PYTHONPATH)
export PYTHONPATH

# Test specific settings
COCOTB_LOG_LEVEL = INFO

# Test targets
.PHONY: test waves help compile_only test_basic test_config test_edge test_performance test_protocol test_stats test_all run

# Compile-only target for CI/CD syntax validation
compile_only:
	@echo "Running compile-only check for CI/CD..."
	@echo "Project root: $(PROJECT_ROOT)"
	@echo "Verilog sources: $(VERILOG_SOURCES)"
	@if command -v verilator >/dev/null 2>&1; then \
		echo "Running Verilator syntax check..."; \
		verilator --lint-only --sv \
			+incdir+$(PROJECT_ROOT)/src \
			+incdir+$(PROJECT_ROOT)/plugin/p2p/box_250mhz/$(MODULE_NAME)/src \
			+incdir+$(PROJECT_ROOT)/plugin/p2p/box_250mhz/common \
			--language 1800-2012 \
			-Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-GENUNNAMED -Wno-IMPORTSTAR -Wno-VARHIDDEN -Wno-fatal \
			$(VERILOG_SOURCES) --top-module $(TOPLEVEL) || (echo "❌ Verilator syntax check failed" && exit 1); \
		echo "✅ Verilator syntax check passed"; \
	else \
		echo "⚠️  Verilator not found, skipping syntax check"; \
	fi
	@echo "✅ Compile-only check completed"

# Default test
test: test_basic

# Individual test suites
test_basic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_filter_basic_functionality

test_config:
	$(MAKE) run MODULE=test_filter_config TESTCASE=test_configuration_suite

test_edge:
	$(MAKE) run MODULE=test_filter_edge TESTCASE=test_edge_cases_suite

test_performance:
	$(MAKE) run MODULE=test_filter_performance TESTCASE=test_performance_suite

test_protocol:
	$(MAKE) run MODULE=test_filter_protocol TESTCASE=test_protocol_comprehensive

test_stats:
	$(MAKE) run MODULE=test_filter_stats TESTCASE=test_statistics_comprehensive

# Run all comprehensive test suites
test_all:
	@echo "Running all comprehensive test suites..."
	$(MAKE) test_basic
	$(MAKE) test_config
	$(MAKE) test_edge
	$(MAKE) test_performance
	$(MAKE) test_protocol
	$(MAKE) test_stats

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
	@echo "  compile_only      - Run syntax check only (for CI/CD)"
	@echo ""
	@echo "Environment variables:"
	@echo "  SIM           - Simulator (verilator, questa, xcelium, vcs) [default: verilator]"
	@echo "  PROJECT_ROOT  - Project root directory [default: ../../../..]"

# Include Cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
