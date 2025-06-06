# Cocotb Makefile for OpenNIC Filter RX Pipeline Tests

TOPLEVEL_LANG = verilog
SIM = verilator

# DUT module - use the testbench wrapper
DUT = tb_filter_rx_pipeline
TOPLEVEL = $(DUT)

# Test module
MODULE = test_filter_basic

# Source files - include packages first, then modules
VERILOG_SOURCES += $(PWD)/../../../plugin/p2p/box_250mhz/common/cfg_reg_pkg.sv
VERILOG_SOURCES += $(PWD)/../../../plugin/p2p/box_250mhz/common/packet_pkg.sv
VERILOG_SOURCES += $(PWD)/../../../plugin/p2p/box_250mhz/filter_rx_pipeline/src/filter_rx_pipeline.sv
VERILOG_SOURCES += $(PWD)/tb_filter_rx_pipeline.sv

# Include directories
VERILOG_INCLUDE_DIRS += $(PWD)/../../../plugin/p2p/box_250mhz/common
VERILOG_INCLUDE_DIRS += $(PWD)/../../../src

# Simulator specific settings for SystemVerilog
COMPILE_ARGS += --language 1800-2012
COMPILE_ARGS += -Wno-fatal

# Additional simulator args
SIM_ARGS += 

# Test specific settings
COCOTB_LOG_LEVEL = INFO

include $(shell cocotb-config --makefiles)/Makefile.sim
