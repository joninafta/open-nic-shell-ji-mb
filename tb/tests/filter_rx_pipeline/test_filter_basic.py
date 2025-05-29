"""
Basic test for filter_rx_pipeline module.
Demonstrates the testbench environment usage.
"""

import cocotb
from cocotb.triggers import Timer
import os
import sys
import yaml

# Add tb directory to Python path for imports
project_root = os.environ.get('PROJECT_ROOT', '../../../..')
tb_path = os.path.join(project_root, 'tb')
tb_path_abs = os.path.abspath(tb_path)
print(f"DEBUG: PROJECT_ROOT = {project_root}")
print(f"DEBUG: tb_path = {tb_path}")
print(f"DEBUG: tb_path_abs = {tb_path_abs}")
print(f"DEBUG: tb_path exists = {os.path.exists(tb_path_abs)}")
if tb_path_abs not in sys.path:
    sys.path.insert(0, tb_path_abs)
print(f"DEBUG: sys.path = {sys.path[:3]}")  # Print first 3 entries

# Import the testbench environment
from tb.env import FilterRxPipelineEnvironment, Config
from tb.utils import create_standard_testbench_clocks, opennic_standard_reset


@cocotb.test()
async def test_filter_basic_functionality(dut):
    """Basic functionality test for filter_rx_pipeline."""
    
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


@cocotb.test()
async def test_filter_stress(dut):
    """Stress test with many packets."""
    
    # Load configuration
    config = Config()  # Use default config for stress test
    
    # Create clocks and reset
    clock_gen = await create_standard_testbench_clocks(dut, "250mhz")
    await Timer(100, units='ns')
    await opennic_standard_reset(dut, dut.aclk)
    
    # Create environment
    env = FilterRxPipelineEnvironment(dut, config)
    
    try:
        await env.start()
        
        # Run stress test with 50 packets
        await env.run_stress_test(num_packets=50)
        
        # Check results
        status = env.get_environment_status()
        filter_stats = status['filter_stats']
        
        cocotb.log.info(f"Stress test completed: {filter_stats}")
        
        # Verify some packets passed
        if filter_stats['packets_passed'] == 0:
            raise cocotb.result.TestFailure("No packets passed in stress test")
            
    finally:
        await env.stop()
        await clock_gen.stop_all_clocks()


@cocotb.test()
async def test_filter_coverage(dut):
    """Test focused on achieving coverage goals."""
    
    config = Config()
    
    # Setup
    clock_gen = await create_standard_testbench_clocks(dut, "250mhz")
    await Timer(100, units='ns')
    await opennic_standard_reset(dut, dut.aclk)
    
    env = FilterRxPipelineEnvironment(dut, config)
    
    try:
        await env.start()
        
        # Run multiple test sequences to improve coverage
        for i in range(3):
            cocotb.log.info(f"Coverage test iteration {i+1}/3")
            await env.run_basic_test()
            
        # Check coverage
        coverage_percent = env.coverage.get_coverage_percent()
        cocotb.log.info(f"Final coverage: {coverage_percent:.1f}%")
        
        # Report detailed coverage
        env.coverage.report_coverage(detailed=True)
        
    finally:
        await env.stop()
        await clock_gen.stop_all_clocks()
