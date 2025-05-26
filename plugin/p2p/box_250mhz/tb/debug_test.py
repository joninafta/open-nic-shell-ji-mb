#!/usr/bin/env python3
"""
Debug test to understand the filtering logic
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
import logging

from plugin.p2p.box_250mhz.filter_rx_pipeline.tb.tests.test_filter_rx_pipeline import FilterRxPipelineTestbench

logger = logging.getLogger(__name__)

@cocotb.test()
async def debug_filter_logic(dut):
    """Debug the filter matching logic"""
    tb = FilterRxPipelineTestbench(dut)
    await tb.reset_dut()
    
    # Configure only rule 0 with a specific IP, ensure rule 1 is non-matching
    dut.cfg_reg_filter_rules_0_ipv4_addr.value = 0xC0A80101  # 192.168.1.1
    dut.cfg_reg_filter_rules_0_ipv6_addr.value = 0
    dut.cfg_reg_filter_rules_0_port.value = 0  # Wildcard
    
    dut.cfg_reg_filter_rules_1_ipv4_addr.value = 0xC0A80199  # 192.168.1.153
    dut.cfg_reg_filter_rules_1_ipv6_addr.value = 0
    dut.cfg_reg_filter_rules_1_port.value = 9999
    
    await ClockCycles(dut.aclk, 10)
    
    # Print current configuration
    logger.info(f"Rule0 IPv4: 0x{dut.cfg_reg_filter_rules_0_ipv4_addr.value:08x}")
    logger.info(f"Rule0 port: {dut.cfg_reg_filter_rules_0_port.value}")
    logger.info(f"Rule1 IPv4: 0x{dut.cfg_reg_filter_rules_1_ipv4_addr.value:08x}")
    logger.info(f"Rule1 port: {dut.cfg_reg_filter_rules_1_port.value}")
    
    # Test packet that should match rule 0
    test_packet = tb.packet_gen.create_ipv4_packet(
        src_ip="192.168.1.1",
        dst_ip="10.0.0.1",
        src_port=12345,
        dst_port=80,
        payload_size=64
    )
    
    logger.info("Sending test packet that should match rule 0...")
    await tb.s_axis_driver.send_packet(test_packet)
    
    # Wait and check what happened
    await ClockCycles(dut.aclk, 20)
    
    logger.info(f"Total packets: {dut.total_packets.value}")
    logger.info(f"Rule0 hits: {dut.rule0_hit_count.value}")
    logger.info(f"Rule1 hits: {dut.rule1_hit_count.value}")
    logger.info(f"Dropped packets: {dut.dropped_packets.value}")
    
    # Test packet that should NOT match any rule
    test_packet2 = tb.packet_gen.create_ipv4_packet(
        src_ip="192.168.1.2",  # Different IP
        dst_ip="10.0.0.1",
        src_port=12345,
        dst_port=80,
        payload_size=64
    )
    
    logger.info("Sending test packet that should NOT match any rule...")
    await tb.s_axis_driver.send_packet(test_packet2)
    
    # Wait and check what happened
    await ClockCycles(dut.aclk, 20)
    
    logger.info(f"Total packets: {dut.total_packets.value}")
    logger.info(f"Rule0 hits: {dut.rule0_hit_count.value}")
    logger.info(f"Rule1 hits: {dut.rule1_hit_count.value}")
    logger.info(f"Dropped packets: {dut.dropped_packets.value}")
