"""
Basic test for filter_rx_pipeline module.
Demonstrates the testbench environment usage with additional simple tests.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, ClockCycles
import os
import sys
import yaml
import random

# Add project root to Python path to allow importing tb module  
# Get the project root directory relative to the current test file location
current_test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_test_dir, '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the testbench environment (if available)
try:
    from tb.env import FilterRxPipelineEnvironment, Config
    from tb.utils import create_standard_testbench_clocks, opennic_standard_reset
    ENV_AVAILABLE = True
except ImportError:
    ENV_AVAILABLE = False
    cocotb.log.warning("Full testbench environment not available, using simple tests")

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
    if DEBUGPY_AVAILABLE and os.environ.get('COCOTB_DEBUG'):
        debug_port = int(os.environ.get('COCOTB_DEBUG_PORT', '5678'))
        debugpy.listen(('localhost', debug_port))
        print(f"Waiting for debugger on port {debug_port}...")
        debugpy.wait_for_client()
        print("Debugger attached!")
    
    # Generate a 250MHz clock (4ns period)
    clock = Clock(dut.aclk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Log initial state
    dut._log.info("Starting basic clock and reset test")
    dut._log.info(f"Initial time: {cocotb.simulator.get_sim_time()}")
    
    # Reset sequence
    dut.aresetn.value = 0
    dut._log.info("Asserting reset...")
    
    # Wait for a few clock cycles with reset asserted
    await ClockCycles(dut.aclk, 5)
    dut._log.info(f"Time after 5 cycles with reset: {cocotb.simulator.get_sim_time()}")
    
    # Release reset
    dut.aresetn.value = 1
    dut._log.info("Releasing reset...")
    
    # Wait for a few more clock cycles
    await ClockCycles(dut.aclk, 10)
    dut._log.info(f"Time after 10 cycles post-reset: {cocotb.simulator.get_sim_time()}")
    
    # Verify we've progressed in time
    current_time = cocotb.simulator.get_sim_time()
    # Extract nanoseconds from the time tuple
    time_ns = current_time[1] if isinstance(current_time, tuple) else current_time
    assert time_ns > 0, f"Time should have progressed beyond 0, but is {time_ns}"
    
    dut._log.info(f"✅ SUCCESS: Time has progressed to {time_ns} ns")


@cocotb.test()
async def test_axi_stream_passthrough(dut):
    """Test AXI-Stream passthrough functionality"""
    
    # Generate clock
    clock = Clock(dut.aclk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.aresetn.value = 0
    await ClockCycles(dut.aclk, 5)
    dut.aresetn.value = 1
    await ClockCycles(dut.aclk, 5)
    
    dut._log.info("Testing AXI-Stream passthrough...")
    
    # Initialize AXI-Stream signals
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tkeep.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tuser.value = 0
    
    dut.m_axis_tready.value = 1  # Ready to receive data
    
    await ClockCycles(dut.aclk, 5)
    
    # Send a simple packet
    test_data = 0x123456789ABCDEF0
    dut.s_axis_tdata.value = test_data
    dut.s_axis_tkeep.value = 0xFF  # All bytes valid
    dut.s_axis_tvalid.value = 1
    dut.s_axis_tlast.value = 1  # Single-cycle packet
    
    await RisingEdge(dut.aclk)
    
    # Wait for ready
    while not dut.s_axis_tready.value:
        await RisingEdge(dut.aclk)
    
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tlast.value = 0
    
    # Check if data appears on output (may take a few cycles)
    await ClockCycles(dut.aclk, 10)
    
    dut._log.info("✅ AXI-Stream passthrough test completed")


async def run_random_packets(dut, num_packets=10):
    """Helper function to send random packets"""
    
    for i in range(num_packets):
        # Random packet data
        packet_data = random.randint(0, 2**64 - 1)
        packet_keep = random.randint(1, 0xFF)
        
        dut.s_axis_tdata.value = packet_data
        dut.s_axis_tkeep.value = packet_keep
        dut.s_axis_tvalid.value = 1
        dut.s_axis_tlast.value = 1  # Single-cycle packets for simplicity
        
        await RisingEdge(dut.aclk)
        while not dut.s_axis_tready.value:
            await RisingEdge(dut.aclk)
        
        dut.s_axis_tvalid.value = 0
        dut.s_axis_tlast.value = 0
        
        # Random delay between packets
        await ClockCycles(dut.aclk, random.randint(1, 5))
        
        dut._log.info(f"Sent packet {i+1}/{num_packets}: 0x{packet_data:016x}")


@cocotb.test()
async def test_packet_processing(dut):
    """Test processing of multiple packets"""
    
    # Generate clock
    clock = Clock(dut.aclk, 4, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset sequence
    dut.aresetn.value = 0
    await ClockCycles(dut.aclk, 5)
    dut.aresetn.value = 1
    await ClockCycles(dut.aclk, 5)
    
    dut._log.info("Testing packet processing with multiple packets...")
    
    # Initialize signals
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tkeep.value = 0
    dut.s_axis_tlast.value = 0
    dut.s_axis_tuser.value = 0
    dut.m_axis_tready.value = 1
    
    await ClockCycles(dut.aclk, 5)
    
    # Send random packets
    await run_random_packets(dut, 5)
    
    # Let processing complete
    await ClockCycles(dut.aclk, 20)
    
    dut._log.info("✅ Packet processing test completed")


# Comprehensive tests using full environment (if available)
if ENV_AVAILABLE:
    @cocotb.test()
    async def test_filter_basic_functionality(dut):
        """Basic functionality test for filter_rx_pipeline using full environment."""
        
        # Load test configuration
        config_path = os.path.join(os.environ.get('PROJECT_ROOT', '.'), 
                                  'configs/tests/filter_rx_pipeline_basic.yaml')
        
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            config = Config.from_dict(config_dict)
        except FileNotFoundError:
            # Fallback to default config if file not found
            cocotb.log.warning(f"Config file not found: {config_path}, using defaults")
            config = Config()
            
        # Create and start clocks
        clock_gen = await create_standard_testbench_clocks(dut, "250mhz")
        
        # Small delay to let clocks stabilize
        await Timer(100, units='ns')
        
        # Reset the DUT
        await opennic_standard_reset(dut, dut.aclk)
        
        # Create testbench environment
        env = FilterRxPipelineEnvironment(dut, config)
        
        try:
            # Start the environment
            await env.start()
            
            # Run basic test
            await env.run_basic_test()
            
            # Get final status
            status = env.get_environment_status()
            cocotb.log.info(f"Test completed with status: {status}")
            
            # Check results
            filter_stats = status['filter_stats']
            if filter_stats['packets_passed'] == 0:
                raise cocotb.result.TestFailure("No packets passed through filter")
                
            cocotb.log.info(f"Filter test passed: {filter_stats['packets_passed']} packets passed")
            
        finally:
            # Stop the environment
            await env.stop()
            
            # Stop clocks
            await clock_gen.stop_all_clocks()


if __name__ == "__main__":
    # This allows running the test file directly for debugging
    import sys
    print("This is a Cocotb test file. Run it using 'make' in the test directory.")
    print("Available tests:")
    print("  - test_clock_and_reset")
    print("  - test_axi_stream_passthrough")
    print("  - test_packet_processing")
    if ENV_AVAILABLE:
        print("  - test_filter_basic_functionality")
