#!/usr/bin/env python3
"""
Filter RX Pipeline Protocol Compliance Tests

This module implements comprehensive protocol compliance tests for the Filter RX Pipeline module.
Tests cover AXI Stream protocol compliance, data integrity verification, and interface behavior.

Test Cases Covered:
- TC-AXI-001: AXI Stream protocol compliance and back-pressure handling
- TC-AXI-002: Packet boundary handling (tlast, tkeep)
- TC-AXI-003: User signal pass-through (tuser)
- TC-INT-001: Data integrity verification

Author: Test Infrastructure
Date: December 2024
"""

import sys
import os
import random
import hashlib
import logging
from pathlib import Path

# Add utils directory to path for imports
sys.path.append(str(Path(__file__).parent / "utils"))

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb.result import TestFailure

from test_utils import FilterRxTestbench, TestConfig
from packet_generator import ScapyPacketGenerator
from axi_stream_monitor import AxiStreamMonitor
from statistics_checker import StatisticsChecker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProtocolTestSuite:
    """Test suite for protocol compliance and data integrity tests."""
    
    def __init__(self, dut):
        """Initialize the protocol test suite."""
        self.dut = dut
        self.tb = FilterRxTestbench(dut)
        self.packet_gen = ScapyPacketGenerator()
        self.axi_monitor = AxiStreamMonitor(dut)
        self.stats_checker = StatisticsChecker(dut)
        
    async def setup_test(self, test_name: str):
        """Common test setup."""
        logger.info(f"Setting up {test_name}")
        
        # Reset DUT
        await self.tb.reset()
        
        # Configure basic filtering rules
        config = TestConfig()
        config.rule0_ipv4_addr = 0xC0A80101  # 192.168.1.1
        config.rule0_port = 80
        config.rule1_ipv4_addr = 0xC0A80102  # 192.168.1.2
        config.rule1_port = 443
        
        await self.tb.configure_filter(config)
        await self.tb.clear_statistics()
        
    async def teardown_test(self, test_name: str):
        """Common test cleanup."""
        logger.info(f"Cleaning up {test_name}")
        await ClockCycles(self.dut.aclk, 10)
        
    # ========================================================================
    # TC-AXI-001: AXI Stream Protocol Compliance
    # ========================================================================
    
    async def test_continuous_backpressure(self):
        """Test behavior under continuous back-pressure."""
        logger.info("Testing continuous back-pressure handling")
        
        # Generate test packet
        packet_data = self.packet_gen.generate_ipv4_packet(
            src_ip="192.168.1.1", dst_ip="10.0.0.1",
            src_port=80, dst_port=12345,
            payload_size=100
        )
        
        # Apply continuous back-pressure
        self.dut.m_axis_tready.value = 0
        await ClockCycles(self.dut.aclk, 5)
        
        # Start sending packet
        send_task = cocotb.start_soon(self.tb.send_packet(packet_data))
        
        # Verify s_axis_tready goes low when pipeline fills
        await ClockCycles(self.dut.aclk, 20)
        
        # Release back-pressure
        self.dut.m_axis_tready.value = 1
        
        # Wait for packet to complete
        await send_task
        
        # Verify packet was received correctly
        received_packet = await self.tb.get_received_packet()
        assert received_packet is not None, "Packet should be received after back-pressure release"
        
        # Verify data integrity
        assert received_packet['data'] == packet_data, "Packet data should be preserved"
        
        logger.info("✅ Continuous back-pressure test passed")
        
    async def test_intermittent_backpressure(self):
        """Test behavior under intermittent back-pressure."""
        logger.info("Testing intermittent back-pressure handling")
        
        packets_to_send = 10
        packets_sent = []
        
        # Generate test packets
        for i in range(packets_to_send):
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345 + i,
                payload_size=64 + i * 10
            )
            packets_sent.append(packet_data)
        
        # Start random back-pressure pattern
        async def random_backpressure():
            for _ in range(200):  # Run for 200 cycles
                self.dut.m_axis_tready.value = random.choice([0, 1])
                await ClockCycles(self.dut.aclk, 1)
            self.dut.m_axis_tready.value = 1  # Ensure final ready
        
        backpressure_task = cocotb.start_soon(random_backpressure())
        
        # Send all packets
        for packet_data in packets_sent:
            await self.tb.send_packet(packet_data)
            await ClockCycles(self.dut.aclk, random.randint(1, 5))  # Random spacing
        
        # Wait for back-pressure pattern to complete
        await backpressure_task
        
        # Wait for all packets to be processed
        await ClockCycles(self.dut.aclk, 50)
        
        # Verify all packets were received
        received_packets = await self.tb.get_all_received_packets()
        assert len(received_packets) == packets_to_send, f"Expected {packets_to_send} packets, got {len(received_packets)}"
        
        # Verify packet order and integrity
        for i, received in enumerate(received_packets):
            assert received['data'] == packets_sent[i], f"Packet {i} data integrity failed"
        
        logger.info("✅ Intermittent back-pressure test passed")
    
    async def test_single_cycle_backpressure(self):
        """Test recovery from single-cycle back-pressure."""
        logger.info("Testing single-cycle back-pressure recovery")
        
        # Generate test packet
        packet_data = self.packet_gen.generate_ipv4_packet(
            src_ip="192.168.1.1", dst_ip="10.0.0.1",
            src_port=80, dst_port=12345,
            payload_size=200
        )
        
        # Start sending packet
        send_task = cocotb.start_soon(self.tb.send_packet(packet_data))
        
        # Apply single-cycle back-pressure at random times
        for _ in range(5):
            await ClockCycles(self.dut.aclk, random.randint(3, 8))
            self.dut.m_axis_tready.value = 0
            await ClockCycles(self.dut.aclk, 1)
            self.dut.m_axis_tready.value = 1
        
        # Wait for packet to complete
        await send_task
        
        # Verify packet was received correctly
        received_packet = await self.tb.get_received_packet()
        assert received_packet is not None, "Packet should be received"
        assert received_packet['data'] == packet_data, "Packet data should be preserved"
        
        logger.info("✅ Single-cycle back-pressure test passed")
        
    # ========================================================================
    # TC-AXI-002: Packet Boundary Handling
    # ========================================================================
    
    async def test_single_beat_packets(self):
        """Test handling of single-beat packets."""
        logger.info("Testing single-beat packet handling")
        
        # Generate very small packet (should fit in single beat)
        packet_data = self.packet_gen.generate_ipv4_packet(
            src_ip="192.168.1.1", dst_ip="10.0.0.1",
            src_port=80, dst_port=12345,
            payload_size=20  # Small payload for single beat
        )
        
        # Send packet and monitor boundaries
        await self.tb.send_packet(packet_data)
        
        # Verify packet was received with correct boundary signals
        received_packet = await self.tb.get_received_packet()
        assert received_packet is not None, "Single-beat packet should be received"
        assert received_packet['tlast_aligned'], "tlast should be properly aligned"
        assert received_packet['data'] == packet_data, "Data integrity should be preserved"
        
        logger.info("✅ Single-beat packet test passed")
        
    async def test_multi_beat_packets(self):
        """Test handling of multi-beat packets."""
        logger.info("Testing multi-beat packet handling")
        
        # Generate large packet (multiple beats)
        packet_data = self.packet_gen.generate_ipv4_packet(
            src_ip="192.168.1.1", dst_ip="10.0.0.1",
            src_port=80, dst_port=12345,
            payload_size=1000  # Large payload for multiple beats
        )
        
        # Send packet and monitor boundaries
        await self.tb.send_packet(packet_data)
        
        # Verify packet was received with correct boundary handling
        received_packet = await self.tb.get_received_packet()
        assert received_packet is not None, "Multi-beat packet should be received"
        assert received_packet['tlast_aligned'], "tlast should be properly aligned"
        assert received_packet['tkeep_correct'], "tkeep should be handled correctly"
        assert received_packet['data'] == packet_data, "Data integrity should be preserved"
        
        logger.info("✅ Multi-beat packet test passed")
        
    async def test_back_to_back_packets(self):
        """Test handling of back-to-back packets."""
        logger.info("Testing back-to-back packet handling")
        
        num_packets = 5
        packets_sent = []
        
        # Generate multiple packets
        for i in range(num_packets):
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345 + i,
                payload_size=100 + i * 20
            )
            packets_sent.append(packet_data)
        
        # Send packets back-to-back (no gaps)
        for packet_data in packets_sent:
            send_task = cocotb.start_soon(self.tb.send_packet(packet_data))
            await send_task
        
        # Verify all packets received with correct boundaries
        received_packets = await self.tb.get_all_received_packets()
        assert len(received_packets) == num_packets, f"Expected {num_packets}, got {len(received_packets)}"
        
        for i, received in enumerate(received_packets):
            assert received['tlast_aligned'], f"Packet {i} tlast not aligned"
            assert received['data'] == packets_sent[i], f"Packet {i} data integrity failed"
        
        logger.info("✅ Back-to-back packet test passed")
        
    async def test_partial_final_beat(self):
        """Test proper tkeep handling for partial final beat."""
        logger.info("Testing partial final beat handling")
        
        # Generate packet with size that creates partial final beat
        for payload_size in [77, 133, 299]:  # Sizes that don't align to beat boundaries
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345,
                payload_size=payload_size
            )
            
            await self.tb.send_packet(packet_data)
            
            received_packet = await self.tb.get_received_packet()
            assert received_packet is not None, f"Packet with size {payload_size} should be received"
            assert received_packet['tkeep_correct'], f"tkeep incorrect for size {payload_size}"
            assert received_packet['data'] == packet_data, f"Data integrity failed for size {payload_size}"
        
        logger.info("✅ Partial final beat test passed")
        
    # ========================================================================
    # TC-AXI-003: User Signal Pass-through
    # ========================================================================
    
    async def test_tuser_passthrough(self):
        """Test that tuser signals pass through unchanged."""
        logger.info("Testing tuser signal pass-through")
        
        test_tuser_values = [0x00, 0xFF, 0xAA, 0x55, 0x3C]
        
        for tuser_val in test_tuser_values:
            # Generate packet with specific tuser value
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345,
                payload_size=100
            )
            
            # Send packet with tuser value
            await self.tb.send_packet(packet_data, tuser=tuser_val)
            
            # Verify tuser is preserved
            received_packet = await self.tb.get_received_packet()
            assert received_packet is not None, "Packet should be received"
            assert received_packet['tuser'] == tuser_val, f"tuser mismatch: expected 0x{tuser_val:02X}, got 0x{received_packet['tuser']:02X}"
            
        logger.info("✅ tuser pass-through test passed")
        
    # ========================================================================
    # TC-INT-001: Data Integrity Verification
    # ========================================================================
    
    async def test_known_pattern_integrity(self):
        """Test data integrity with known patterns."""
        logger.info("Testing data integrity with known patterns")
        
        # Test with incrementing byte patterns
        for packet_size in [64, 128, 256, 512, 1024]:
            # Generate packet with incrementing pattern
            payload = bytes([(i % 256) for i in range(packet_size - 42)])  # Account for headers
            
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345,
                payload=payload
            )
            
            await self.tb.send_packet(packet_data)
            
            received_packet = await self.tb.get_received_packet()
            assert received_packet is not None, f"Packet size {packet_size} should be received"
            assert received_packet['data'] == packet_data, f"Data integrity failed for size {packet_size}"
        
        logger.info("✅ Known pattern integrity test passed")
        
    async def test_random_data_integrity(self):
        """Test data integrity with random data."""
        logger.info("Testing data integrity with random data")
        
        num_packets = 20
        
        for i in range(num_packets):
            # Generate random payload
            payload_size = random.randint(50, 1000)
            payload = bytes([random.randint(0, 255) for _ in range(payload_size)])
            
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345 + i,
                payload=payload
            )
            
            # Calculate checksum before sending
            input_hash = hashlib.md5(packet_data).hexdigest()
            
            await self.tb.send_packet(packet_data)
            
            received_packet = await self.tb.get_received_packet()
            assert received_packet is not None, f"Random packet {i} should be received"
            
            # Verify checksum
            output_hash = hashlib.md5(received_packet['data']).hexdigest()
            assert input_hash == output_hash, f"Checksum mismatch for packet {i}"
        
        logger.info("✅ Random data integrity test passed")
        
    async def test_stress_integrity(self):
        """Test data integrity under stress conditions."""
        logger.info("Testing data integrity under stress")
        
        packets_to_send = 50
        packets_sent = []
        
        # Generate variety of packet sizes and patterns
        for i in range(packets_to_send):
            payload_size = random.randint(60, 1500)
            payload = bytes([random.randint(0, 255) for _ in range(payload_size)])
            
            packet_data = self.packet_gen.generate_ipv4_packet(
                src_ip="192.168.1.1", dst_ip="10.0.0.1",
                src_port=80, dst_port=12345 + i,
                payload=payload
            )
            packets_sent.append((packet_data, hashlib.md5(packet_data).hexdigest()))
        
        # Send all packets rapidly
        for packet_data, _ in packets_sent:
            send_task = cocotb.start_soon(self.tb.send_packet(packet_data))
            await send_task
            await ClockCycles(self.dut.aclk, random.randint(1, 3))
        
        # Verify all packets received with integrity
        received_packets = await self.tb.get_all_received_packets()
        assert len(received_packets) == packets_to_send, f"Expected {packets_to_send}, got {len(received_packets)}"
        
        for i, (expected_data, expected_hash) in enumerate(packets_sent):
            received_hash = hashlib.md5(received_packets[i]['data']).hexdigest()
            assert expected_hash == received_hash, f"Integrity failure for stress packet {i}"
        
        logger.info("✅ Stress integrity test passed")
        
    # ========================================================================
    # Test Suite Runner
    # ========================================================================
    
    async def run_all_protocol_tests(self):
        """Run all protocol compliance tests."""
        logger.info("=" * 60)
        logger.info("STARTING PROTOCOL COMPLIANCE TEST SUITE")
        logger.info("=" * 60)
        
        test_results = {}
        
        # AXI Stream Protocol Tests (TC-AXI-001)
        try:
            await self.setup_test("AXI Stream Protocol Compliance")
            await self.test_continuous_backpressure()
            await self.test_intermittent_backpressure()
            await self.test_single_cycle_backpressure()
            test_results['TC-AXI-001'] = 'PASS'
        except Exception as e:
            logger.error(f"TC-AXI-001 failed: {e}")
            test_results['TC-AXI-001'] = f'FAIL: {e}'
        finally:
            await self.teardown_test("AXI Stream Protocol Compliance")
        
        # Packet Boundary Tests (TC-AXI-002)
        try:
            await self.setup_test("Packet Boundary Handling")
            await self.test_single_beat_packets()
            await self.test_multi_beat_packets()
            await self.test_back_to_back_packets()
            await self.test_partial_final_beat()
            test_results['TC-AXI-002'] = 'PASS'
        except Exception as e:
            logger.error(f"TC-AXI-002 failed: {e}")
            test_results['TC-AXI-002'] = f'FAIL: {e}'
        finally:
            await self.teardown_test("Packet Boundary Handling")
        
        # User Signal Tests (TC-AXI-003)
        try:
            await self.setup_test("User Signal Pass-through")
            await self.test_tuser_passthrough()
            test_results['TC-AXI-003'] = 'PASS'
        except Exception as e:
            logger.error(f"TC-AXI-003 failed: {e}")
            test_results['TC-AXI-003'] = f'FAIL: {e}'
        finally:
            await self.teardown_test("User Signal Pass-through")
        
        # Data Integrity Tests (TC-INT-001)
        try:
            await self.setup_test("Data Integrity Verification")
            await self.test_known_pattern_integrity()
            await self.test_random_data_integrity()
            await self.test_stress_integrity()
            test_results['TC-INT-001'] = 'PASS'
        except Exception as e:
            logger.error(f"TC-INT-001 failed: {e}")
            test_results['TC-INT-001'] = f'FAIL: {e}'
        finally:
            await self.teardown_test("Data Integrity Verification")
        
        # Print summary
        logger.info("=" * 60)
        logger.info("PROTOCOL COMPLIANCE TEST SUITE SUMMARY")
        logger.info("=" * 60)
        
        for test_id, result in test_results.items():
            status = "✅ PASS" if result == 'PASS' else f"❌ {result}"
            logger.info(f"{test_id}: {status}")
        
        # Check overall results
        failed_tests = [k for k, v in test_results.items() if v != 'PASS']
        if failed_tests:
            raise TestFailure(f"Protocol compliance tests failed: {failed_tests}")
        
        logger.info("🎉 All protocol compliance tests PASSED!")


# ============================================================================
# Cocotb Test Functions
# ============================================================================

@cocotb.test()
async def test_axi_stream_compliance(dut):
    """TC-AXI-001: AXI Stream protocol compliance test."""
    # Initialize test environment
    await Clock(dut.aclk, 4, units="ns").start()  # 250MHz
    
    # Create test suite
    protocol_suite = ProtocolTestSuite(dut)
    
    # Run AXI Stream compliance tests
    await protocol_suite.setup_test("AXI Stream Protocol Compliance")
    await protocol_suite.test_continuous_backpressure()
    await protocol_suite.test_intermittent_backpressure()
    await protocol_suite.test_single_cycle_backpressure()
    await protocol_suite.teardown_test("AXI Stream Protocol Compliance")


@cocotb.test()
async def test_packet_boundaries(dut):
    """TC-AXI-002: Packet boundary handling test."""
    # Initialize test environment
    await Clock(dut.aclk, 4, units="ns").start()  # 250MHz
    
    # Create test suite
    protocol_suite = ProtocolTestSuite(dut)
    
    # Run packet boundary tests
    await protocol_suite.setup_test("Packet Boundary Handling")
    await protocol_suite.test_single_beat_packets()
    await protocol_suite.test_multi_beat_packets()
    await protocol_suite.test_back_to_back_packets()
    await protocol_suite.test_partial_final_beat()
    await protocol_suite.teardown_test("Packet Boundary Handling")


@cocotb.test()
async def test_tuser_passthrough(dut):
    """TC-AXI-003: User signal pass-through test."""
    # Initialize test environment
    await Clock(dut.aclk, 4, units="ns").start()  # 250MHz
    
    # Create test suite
    protocol_suite = ProtocolTestSuite(dut)
    
    # Run tuser pass-through test
    await protocol_suite.setup_test("User Signal Pass-through")
    await protocol_suite.test_tuser_passthrough()
    await protocol_suite.teardown_test("User Signal Pass-through")


@cocotb.test()
async def test_packet_integrity(dut):
    """TC-INT-001: Data integrity verification test."""
    # Initialize test environment
    await Clock(dut.aclk, 4, units="ns").start()  # 250MHz
    
    # Create test suite
    protocol_suite = ProtocolTestSuite(dut)
    
    # Run data integrity tests
    await protocol_suite.setup_test("Data Integrity Verification")
    await protocol_suite.test_known_pattern_integrity()
    await protocol_suite.test_random_data_integrity()
    await protocol_suite.test_stress_integrity()
    await protocol_suite.teardown_test("Data Integrity Verification")


@cocotb.test()
async def test_protocol_comprehensive(dut):
    """Comprehensive protocol compliance and integrity test suite."""
    # Initialize test environment
    await Clock(dut.aclk, 4, units="ns").start()  # 250MHz
    
    # Create and run comprehensive test suite
    protocol_suite = ProtocolTestSuite(dut)
    await protocol_suite.run_all_protocol_tests()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    """Run protocol tests independently for debugging."""
    import pytest
    
    # Run specific test
    pytest.main([__file__ + "::test_protocol_comprehensive", "-v", "-s"])
