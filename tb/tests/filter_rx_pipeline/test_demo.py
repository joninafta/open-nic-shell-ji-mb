#!/usr/bin/env python3
"""
Demo test for filter_rx_pipeline module.
Demonstrates basic testbench functionality without complex dependencies.
"""

import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.clock import Clock
import os

@cocotb.test()
async def test_clock_and_reset(dut):
    """Test basic clock and reset functionality."""
    
    # Start clock
    clock = Clock(dut.aclk, 4, units="ns")  # 250MHz clock
    cocotb.start_soon(clock.start())
    
    # Initial reset
    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.m_axis_tready.value = 1
    
    # Wait a few clock cycles
    await Timer(20, units="ns")
    
    # Release reset
    dut.aresetn.value = 1
    await Timer(20, units="ns")
    
    # Test passed
    dut._log.info("✅ Clock and Reset test PASSED")

@cocotb.test()
async def test_basic_interface(dut):
    """Test basic AXI Stream interface signals."""
    
    # Start clock
    clock = Clock(dut.aclk, 4, units="ns")  # 250MHz clock
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tkeep.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tuser.value = 0
    dut.m_axis_tready.value = 1
    
    await Timer(20, units="ns")
    dut.aresetn.value = 1
    await Timer(20, units="ns")
    
    # Check that signals are accessible
    tready_val = dut.s_axis_tready.value
    tvalid_val = dut.m_axis_tvalid.value
    
    dut._log.info(f"s_axis_tready = {tready_val}")
    dut._log.info(f"m_axis_tvalid = {tvalid_val}")
    dut._log.info("✅ Basic Interface test PASSED")

@cocotb.test()
async def test_packet_flow(dut):
    """Test a simple packet flow through the pipeline."""
    
    # Start clock
    clock = Clock(dut.aclk, 4, units="ns")  # 250MHz clock
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tkeep.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tuser.value = 0
    dut.m_axis_tready.value = 1
    
    await Timer(20, units="ns")
    dut.aresetn.value = 1
    await Timer(20, units="ns")
    
    # Send a simple packet
    dut.s_axis_tvalid.value = 1
    dut.s_axis_tdata.value = 0x123456789ABCDEF0  # Simple test data
    dut.s_axis_tkeep.value = 0xFF  # 8 bytes valid
    dut.s_axis_tlast.value = 1     # Single beat packet
    dut.s_axis_tuser.value = 0
    
    # Wait for a few clock cycles
    for i in range(10):
        await RisingEdge(dut.aclk)
        if dut.s_axis_tready.value == 1:
            break
    
    # Clear input
    dut.s_axis_tvalid.value = 0
    
    # Wait for output
    for i in range(20):
        await RisingEdge(dut.aclk)
        if dut.m_axis_tvalid.value == 1:
            dut._log.info(f"Output packet received: data = {dut.m_axis_tdata.value}")
            break
    
    dut._log.info("✅ Packet Flow test COMPLETED")
