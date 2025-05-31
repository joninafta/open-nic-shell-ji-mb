# Filelist for filter_rx_pipeline module testbench
# OpenNIC Shell - Filter RX Pipeline Verification

# Design files
+incdir+$PROJECT_ROOT/src
+incdir+$PROJECT_ROOT/plugin/p2p/box_250mhz/filter_rx_pipeline/src

# Main design file
$PROJECT_ROOT/plugin/p2p/box_250mhz/filter_rx_pipeline/src/filter_rx_pipeline.sv

# Required package files  
$PROJECT_ROOT/src/open_nic_shell_macros.vh

# Utility modules that might be needed
$PROJECT_ROOT/src/utility/axi_stream_register_slice.sv
$PROJECT_ROOT/src/utility/axi_stream_packet_buffer.sv
$PROJECT_ROOT/src/utility/axi_stream_packet_fifo.sv

# Testbench files
$PROJECT_ROOT/tb/tests/filter_rx_pipeline/tb_filter_rx_pipeline.sv

# Define macros for synthesis/simulation
+define+SIMULATION
+define+COCOTB_SIM

# Compile options
+sv
+acc
-timescale 1ns/1ps
