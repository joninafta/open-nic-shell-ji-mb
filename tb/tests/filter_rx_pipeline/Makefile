# Makefile for filter_rx_pipeline Cocotb testbench
# OpenNIC Shell Verification Environment

# Project settings
PROJECT_ROOT ?= $(shell pwd)/../../../..
TB_ROOT = $(PROJECT_ROOT)/tb
MODULE_NAME = filter_rx_pipeline

# Simulator settings
SIM ?= questa
TOPLEVEL_LANG ?= verilog
TOPLEVEL = tb_$(MODULE_NAME)

# Source files
VERILOG_SOURCES = $(TB_ROOT)/tests/$(MODULE_NAME)/tb_$(MODULE_NAME).sv
VERILOG_SOURCES += $(PROJECT_ROOT)/plugin/p2p/box_250mhz/$(MODULE_NAME)/src/$(MODULE_NAME).sv

# Include directories
COMPILE_ARGS += +incdir+$(PROJECT_ROOT)/src
COMPILE_ARGS += +incdir+$(PROJECT_ROOT)/plugin/p2p/box_250mhz/$(MODULE_NAME)/src

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

# Test modules (Python)
MODULE = test_filter_basic

# Python path setup
export PYTHONPATH := $(TB_ROOT):$(PYTHONPATH)
export PROJECT_ROOT := $(PROJECT_ROOT)

# Test targets
.PHONY: test clean waves help

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

# Clean build artifacts
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf sim_build/
	rm -f *.vcd
	rm -f *.wlf
	rm -f *.log
	rm -f transcript
	rm -rf work/
	rm -rf waves.shm/
	rm -rf xcelium.d/
	rm -rf DVEfiles/
	rm -f ucli.key

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
	@echo "  clean         - Clean build artifacts"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Environment variables:"
	@echo "  SIM           - Simulator (questa, xcelium, vcs) [default: questa]"
	@echo "  PROJECT_ROOT  - Project root directory [default: ../../../..]"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Run basic test with default simulator"
	@echo "  make test SIM=xcelium       # Run basic test with Xcelium"
	@echo "  make test_stress             # Run stress test"
	@echo "  make waves                   # View waveforms"

# Include Cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
