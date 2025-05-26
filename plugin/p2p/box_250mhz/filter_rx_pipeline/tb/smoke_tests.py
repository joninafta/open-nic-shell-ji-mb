#!/usr/bin/env python3
"""
Smoke tests for filter_rx_pipeline

Quick tests to verify basic functionality
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
import logging

from packet_generator import PacketGenerator
from axi_stream_driver import AXIStreamDriver, AXIStreamMonitor
from filter_models import FilterModel, FilterRule
from plugin.p2p.box_250mhz.filter_rx_pipeline.tb.test_config import TEST_CONFIG, setup_logging

# Setup logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

class SmokeTestbench:
    """Simplified testbench for smoke tests"""
    
    def __init__(self, dut):
        self.dut = dut
        
        # Start clock
        cocotb.start_soon(Clock(dut.aclk, TEST_CONFIG['clock_period_ns'], units="ns").start())
        
        # Initialize drivers
        self.s_axis_driver = AXIStreamDriver(dut, "s_axis", dut.aclk)
        self.m_axis_monitor = AXIStreamMonitor(dut, "m_axis", dut.aclk)
        
        # Packet generator
        self.packet_gen = PacketGenerator()
        
    async def reset_dut(self):
        """Reset the DUT"""
        self.dut.aresetn.value = 0
        self.dut.m_axis_tready.value = 1
        self._clear_config()
        
        await ClockCycles(self.dut.aclk, TEST_CONFIG['reset_cycles'])
        self.dut.aresetn.value = 1
        await ClockCycles(self.dut.aclk, 5)
        
    def _clear_config(self):
        """Clear all configuration registers"""
        self.dut.cfg_reg_filter_rules_0_ipv4_addr.value = 0
        self.dut.cfg_reg_filter_rules_0_ipv6_addr.value = 0
        self.dut.cfg_reg_filter_rules_0_port.value = 0
        self.dut.cfg_reg_filter_rules_1_ipv4_addr.value = 0
        self.dut.cfg_reg_filter_rules_1_ipv6_addr.value = 0
        self.dut.cfg_reg_filter_rules_1_port.value = 0
        
    def configure_ipv4_rule(self, rule_id, ipv4_addr=None, port=None):
        """Configure IPv4 rule"""
        if rule_id == 0:
            if ipv4_addr is not None:
                self.dut.cfg_reg_filter_rules_0_ipv4_addr.value = ipv4_addr
            if port is not None:
                self.dut.cfg_reg_filter_rules_0_port.value = port
        elif rule_id == 1:
            if ipv4_addr is not None:
                self.dut.cfg_reg_filter_rules_1_ipv4_addr.value = ipv4_addr
            if port is not None:
                self.dut.cfg_reg_filter_rules_1_port.value = port

@cocotb.test()
async def smoke_test_reset(dut):
    """Smoke test: Verify basic reset functionality"""
    tb = SmokeTestbench(dut)
    await tb.reset_dut()
    
    # Check that pipeline is idle
    assert dut.s_axis_tready.value == 1, "s_axis_tready should be high after reset"
    assert dut.m_axis_tvalid.value == 0, "m_axis_tvalid should be low after reset"
    
    # Check counter reset
    assert dut.total_packets.value == 0, "total_packets should be 0 after reset"
    assert dut.rule0_hit_count.value == 0, "rule0_hit_count should be 0 after reset"
    assert dut.rule1_hit_count.value == 0, "rule1_hit_count should be 0 after reset"
    assert dut.dropped_packets.value == 0, "dropped_packets should be 0 after reset"
    
    logger.info("✓ Reset smoke test passed")

@cocotb.test()
async def smoke_test_passthrough(dut):
    """Smoke test: Verify packets pass with wildcard rules"""
    tb = SmokeTestbench(dut)
    await tb.reset_dut()
    
    # Configure wildcard rule (0 = match all)
    tb.configure_ipv4_rule(0, ipv4_addr=0, port=0)
    
    # Create simple IPv4 packet
    packet = tb.packet_gen.create_ipv4_packet(
        src_ip="192.168.1.1",
        dst_ip="10.0.0.1",
        src_port=12345,
        dst_port=80,
        payload_size=64
    )
    
    # Send packet
    await tb.s_axis_driver.send_packet(packet)
    
    # Wait for output
    received = await tb.m_axis_monitor.wait_for_packet(timeout_cycles=100)
    assert received is not None, "Packet should pass with wildcard rule"
    
    # Check counters
    await ClockCycles(dut.aclk, 10)
    assert dut.total_packets.value == 1, "Should count 1 total packet"
    assert dut.rule0_hit_count.value == 1, "Should count 1 rule0 hit"
    assert dut.dropped_packets.value == 0, "Should count 0 dropped packets"
    
    logger.info("✓ Passthrough smoke test passed")

@cocotb.test()
async def smoke_test_drop(dut):
    """Smoke test: Verify packets are dropped when no rules match"""
    tb = SmokeTestbench(dut)
    await tb.reset_dut()
    
    # Configure specific rules that won't match our test packet
    tb.configure_ipv4_rule(0, ipv4_addr=0xC0A80101, port=9999)  # 192.168.1.1:9999
    tb.configure_ipv4_rule(1, ipv4_addr=0xC0A80102, port=8888)  # 192.168.1.2:8888
    
    # Create packet with different source IP and port
    packet = tb.packet_gen.create_ipv4_packet(
        src_ip="10.0.0.1",  # Different from rule
        dst_ip="192.168.1.1",
        src_port=12345,  # Different from rule port
        dst_port=80,
        payload_size=64
    )
    
    # Send packet
    await tb.s_axis_driver.send_packet(packet)
    
    # Verify no output
    received = await tb.m_axis_monitor.wait_for_packet(timeout_cycles=50)
    assert received is None, "Packet should be dropped when no rules match"
    
    # Check counters
    await ClockCycles(dut.aclk, 10)
    assert dut.total_packets.value == 1, "Should count 1 total packet"
    assert dut.rule0_hit_count.value == 0, "Should count 0 rule0 hits"
    assert dut.dropped_packets.value == 1, "Should count 1 dropped packet"
    
    logger.info("✓ Drop smoke test passed")

@cocotb.test()
async def smoke_test_pipeline_flow(dut):
    """Smoke test: Verify pipeline accepts multiple packets"""
    tb = SmokeTestbench(dut)
    await tb.reset_dut()
    
    # Configure wildcard rule
    tb.configure_ipv4_rule(0, ipv4_addr=0, port=0)
    
    # Send multiple packets rapidly
    num_packets = 5
    for i in range(num_packets):
        packet = tb.packet_gen.create_ipv4_packet(
            src_ip=f"192.168.1.{i+1}",
            dst_ip="10.0.0.1",
            src_port=1000+i,
            dst_port=80,
            payload_size=64
        )
        await tb.s_axis_driver.send_packet(packet)
        
        # Small gap between packets
        await ClockCycles(dut.aclk, 2)
    
    # Wait for all packets to be processed
    await ClockCycles(dut.aclk, 100)
    
    # Check that all packets were processed
    assert dut.total_packets.value == num_packets, f"Should count {num_packets} total packets"
    assert dut.rule0_hit_count.value == num_packets, f"Should count {num_packets} rule0 hits"
    assert dut.dropped_packets.value == 0, "Should count 0 dropped packets"
    
    logger.info("✓ Pipeline flow smoke test passed")

@cocotb.test()
async def smoke_test_backpressure(dut):
    """Smoke test: Verify basic backpressure handling"""
    tb = SmokeTestbench(dut)
    await tb.reset_dut()
    
    # Configure rule
    tb.configure_ipv4_rule(0, port=80)
    
    # Apply backpressure
    dut.m_axis_tready.value = 0
    
    # Try to send packet
    packet = tb.packet_gen.create_ipv4_packet(
        src_ip="192.168.1.1",
        dst_ip="10.0.0.1",
        src_port=80,  # Should match rule
        dst_port=8080,
        payload_size=64
    )
    
    # Start sending (should block due to backpressure)
    send_task = cocotb.start_soon(tb.s_axis_driver.send_packet(packet))
    
    # Wait a bit
    await ClockCycles(dut.aclk, 20)
    
    # Should see backpressure effect
    assert dut.s_axis_tready.value == 0, "Should see backpressure on s_axis_tready"
    
    # Release backpressure
    dut.m_axis_tready.value = 1
    
    # Wait for completion
    await send_task
    await ClockCycles(dut.aclk, 10)
    
    # Verify packet was processed
    assert dut.total_packets.value == 1, "Should count 1 total packet"
    assert dut.rule0_hit_count.value == 1, "Should count 1 rule0 hit"
    
    logger.info("✓ Backpressure smoke test passed")

# Quick test runner
if __name__ == "__main__":
    import os
    os.system("make MODULE=smoke_tests")
