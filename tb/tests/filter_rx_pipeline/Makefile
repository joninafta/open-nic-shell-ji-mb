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
MODULE = test_filter_basic

# Python path setup - ensure tb package is importable
PYTHONPATH := $(TB_ROOT):$(PYTHONPATH)
export PYTHONPATH

# Test targets
.PHONY: test waves help

# Default test
test: test_basic

# Individual tests
test_basic:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_filter_basic_functionality

test_stress:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_filter_stress

test_coverage:
	$(MAKE) run MODULE=test_filter_basic TESTCASE=test_filter_coverage

# Run all tests
test_all:
	$(MAKE) test_basic
	$(MAKE) test_stress  
	$(MAKE) test_coverage

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
	@echo "OpenNIC Filter RX Pipeline Testbench"
	@echo ""
	@echo "Available targets:"
	@echo "  test          - Run basic functionality test (default)"
	@echo "  test_basic    - Run basic functionality test"
	@echo "  test_stress   - Run stress test with many packets"
	@echo "  test_coverage - Run coverage-focused test"
	@echo "  test_all      - Run all tests"
	@echo "  waves         - View waveforms"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Environment variables:"
	@echo "  SIM           - Simulator (verilator, questa, xcelium, vcs) [default: verilator]"
	@echo "  PROJECT_ROOT  - Project root directory [default: ../../../..]"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Run basic test with default simulator (Verilator)"
	@echo "  make test SIM=questa        # Run basic test with Questa"
	@echo "  make test_stress             # Run stress test"
	@echo "  make waves                   # View waveforms"

# Include Cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
