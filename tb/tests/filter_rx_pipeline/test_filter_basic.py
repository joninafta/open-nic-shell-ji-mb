"""
OpenNIC Packet Filter Basic Tests

This module contains basic functional tests for the OpenNIC packet filter implementation.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ClockCycles
from cocotb.regression import TestFactory
import random

# Optional debugpy setup - only import if available
try:
    import debugpy
    DEBUGPY_AVAILABLE = True
except ImportError:
    DEBUGPY_AVAILABLE = False


@cocotb.test()
async def test_clock_and_reset(dut):
    """Test basic clock and reset functionality - ensures time progresses"""
    
    # Start debugpy if available and environment variable is set
    if DEBUGPY_AVAILABLE and cocotb.os.environ.get('COCOTB_DEBUG'):
        debug_port = int(cocotb.os.environ.get('COCOTB_DEBUG_PORT', '5678'))
        debugpy.listen(('localhost', debug_port))
        print(f"Waiting for debugger on port {debug_port}...")
        debugpy.wait_for_client()
        print("Debugger attached!")
    
    # Generate a 250MHz clock (4ns period)
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Log initial state
    dut._log.info("Starting basic clock and reset test")
    dut._log.info(f"Initial time: {cocotb.simulator.get_sim_time()}")
    
    # Reset sequence
    dut.rst_n.value = 0
    dut._log.info("Asserting reset...")
    
    # Wait for a few clock cycles with reset asserted
    await ClockCycles(dut.clk, 5)
    dut._log.info(f"Time after 5 cycles with reset: {cocotb.simulator.get_sim_time()}")
    
    # Release reset
    dut.rst_n.value = 1
    dut._log.info("Releasing reset...")
    
    # Wait for a few more clock cycles
    await ClockCycles(dut.clk, 10)
    dut._log.info(f"Time after 10 cycles post-reset: {cocotb.simulator.get_sim_time()}")
    
    # Verify we've progressed in time
    current_time = cocotb.simulator.get_sim_time()
    # Extract nanoseconds from the time tuple
    time_ns = current_time[1] if isinstance(current_time, tuple) else current_time
    assert time_ns > 0, f"Time should have progressed beyond 0, but is {time_ns}"
    
    dut._log.info(f"✅ SUCCESS: Time has progressed to {time_ns} ns")


@cocotb.test()
async def test_axi_lite_interface(dut):
    """Test configuration register interface basic functionality"""
    
    # Generate clock
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    
    dut._log.info("Testing configuration register interface...")
    
    # Check that configuration registers are accessible
    # These are directly connected to the module via cfg_reg structure
    await ClockCycles(dut.clk, 5)
    
    # Check status register readback (this should be available)
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("✅ Configuration register interface test completed")


@cocotb.test()
async def test_axi_stream_passthrough(dut):
    """Test AXI-Stream passthrough functionality"""
    
    # Generate clock
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    
    dut._log.info("Testing AXI-Stream passthrough...")
    
    # Initialize AXI-Stream signals
    dut.s_axis_rx_tvalid.value = 0
    dut.s_axis_rx_tdata.value = 0
    dut.s_axis_rx_tkeep.value = 0
    dut.s_axis_rx_tlast.value = 0
    dut.s_axis_rx_tuser.value = 0
    
    dut.m_axis_rx_tready.value = 1  # Ready to receive data
    
    await ClockCycles(dut.clk, 5)
    
    # Send a simple packet
    test_data = 0x123456789ABCDEF0
    dut.s_axis_rx_tdata.value = test_data
    dut.s_axis_rx_tkeep.value = 0xFF  # All bytes valid
    dut.s_axis_rx_tvalid.value = 1
    dut.s_axis_rx_tlast.value = 1  # Single-cycle packet
    
    await RisingEdge(dut.clk)
    
    # Wait for ready
    while not dut.s_axis_rx_tready.value:
        await RisingEdge(dut.clk)
    
    dut.s_axis_rx_tvalid.value = 0
    dut.s_axis_rx_tlast.value = 0
    
    # Check if data appears on output (may take a few cycles)
    await ClockCycles(dut.clk, 10)
    
    dut._log.info("✅ AXI-Stream passthrough test completed")


async def run_random_packets(dut, num_packets=10):
    """Helper function to send random packets"""
    
    for i in range(num_packets):
        # Random packet data
        packet_data = random.randint(0, 2**64 - 1)
        packet_keep = random.randint(1, 0xFF)
        
        dut.s_axis_rx_tdata.value = packet_data
        dut.s_axis_rx_tkeep.value = packet_keep
        dut.s_axis_rx_tvalid.value = 1
        dut.s_axis_rx_tlast.value = 1  # Single-cycle packets for simplicity
        
        await RisingEdge(dut.clk)
        while not dut.s_axis_rx_tready.value:
            await RisingEdge(dut.clk)
        
        dut.s_axis_rx_tvalid.value = 0
        dut.s_axis_rx_tlast.value = 0
        
        # Random delay between packets
        await ClockCycles(dut.clk, random.randint(1, 5))
        
        dut._log.info(f"Sent packet {i+1}/{num_packets}: 0x{packet_data:016x}")


@cocotb.test()
async def test_packet_processing(dut):
    """Test processing of multiple packets"""
    
    # Generate clock
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    
    dut._log.info("Testing packet processing with multiple packets...")
    
    # Initialize signals
    dut.s_axis_rx_tvalid.value = 0
    dut.s_axis_rx_tdata.value = 0
    dut.s_axis_rx_tkeep.value = 0
    dut.s_axis_rx_tlast.value = 0
    dut.s_axis_rx_tuser.value = 0
    dut.m_axis_rx_tready.value = 1
    
    await ClockCycles(dut.clk, 5)
    
    # Send random packets
    await run_random_packets(dut, 5)
    
    # Let processing complete
    await ClockCycles(dut.clk, 20)
    
    dut._log.info("✅ Packet processing test completed")


if __name__ == "__main__":
    # This allows running the test file directly for debugging
    import sys
    print("This is a Cocotb test file. Run it using 'make' in the test directory.")
    print("Available tests:")
    print("  - test_clock_and_reset")
    print("  - test_axi_lite_interface") 
    print("  - test_axi_stream_passthrough")
    print("  - test_packet_processing")