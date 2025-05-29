"""
Edge case and error condition tests for filter_rx_pipeline.
Tests boundary conditions, malformed packets, and error scenarios.

Test Cases Covered:
- TC-EDGE-001: Malformed packets and error handling
- TC-EDGE-002: Minimum and maximum packet sizes
- TC-EDGE-003: Invalid EtherType handling
- TC-EDGE-004: Truncated packets
- TC-EDGE-005: Back-pressure handling
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.log import SimLog
import random

# Import our utilities
from utils.test_utils import FilterRxTestbench, TestResult, CommonRules
from utils.packet_generator import PacketGenerator, PacketConfig, TestPackets
from utils.statistics_checker import create_statistics_verifier


class TestEdgeCases:
    """Test class for edge cases and error conditions."""
    
    def __init__(self):
        self.log = SimLog("test_edge")
        self.results = []
    
    async def setup_test(self, dut):
        """Common test setup."""
        self.tb = FilterRxTestbench(dut)
        self.checker, self.tracker = create_statistics_verifier(dut)
        
        # Initialize DUT
        await self.tb.reset()
        await self.tb.clear_rules()
        
        # Reset statistics tracking
        self.tracker.reset()
        await self.checker.reset_statistics()
    
    async def teardown_test(self):
        """Common test teardown."""
        await Timer(200, units='ns')  # Longer delay for edge cases

    async def tc_edge_001(self, dut):
        """TC-EDGE-001: Malformed packets and error handling."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-EDGE-001", "Malformed packets and error handling")
        
        try:
            # Configure a basic rule for comparison
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Test 1: Invalid EtherType
            malformed_config = TestPackets.malformed_ethertype_packet(payload_size=64)
            malformed_packet = generator.generate_packet(malformed_config)
            
            await self.tb.send_packet(malformed_packet)
            self.tracker.add_packet_sent(len(malformed_packet), should_pass=False)
            
            # Test 2: Truncated packet (early tlast)
            truncated_config = TestPackets.truncated_packet("192.168.1.1", truncate_at=30)
            truncated_packet = generator.generate_packet(truncated_config)
            
            await self.tb.send_packet(truncated_packet)
            self.tracker.add_packet_sent(len(truncated_packet), should_pass=False)
            
            # Test 3: Valid packet for comparison
            valid_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
            valid_packet = generator.generate_packet(valid_config)
            
            await self.tb.send_packet(valid_packet)
            self.tracker.add_packet_sent(len(valid_packet), should_pass=True, rule_hit=0)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(3)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Malformed packet handling working correctly"
                self.log.info("TC-EDGE-001 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-EDGE-001 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-EDGE-001 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_edge_002(self, dut):
        """TC-EDGE-002: Minimum and maximum packet sizes."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-EDGE-002", "Minimum and maximum packet sizes")
        
        try:
            # Configure rule
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Test various packet sizes
            packet_sizes = [
                0,     # Minimum payload (headers only)
                1,     # Very small payload
                64,    # Small packet
                1500,  # Standard MTU
                9000,  # Jumbo frame
                9216,  # Maximum jumbo frame
            ]
            
            for size in packet_sizes:
                packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=size)
                packet = generator.generate_packet(packet_config)
                
                self.log.info(f"Testing packet size: {len(packet)} bytes (payload: {size})")
                
                await self.tb.send_packet(packet)
                self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                
                # Small delay between packets
                await Timer(50, units='ns')
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(len(packet_sizes))
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Packet size handling working correctly"
                self.log.info("TC-EDGE-002 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-EDGE-002 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-EDGE-002 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_edge_003(self, dut):
        """TC-EDGE-003: Invalid EtherType handling."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-EDGE-003", "Invalid EtherType handling")
        
        try:
            # Configure rule (should not match invalid EtherTypes)
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Test various invalid EtherTypes
            invalid_ethertypes = [
                0x1234,  # Random invalid type
                0x0000,  # Zero
                0xFFFF,  # All ones
                0x0806,  # ARP (should not match IP rules)
                0x86DD,  # IPv6 (but we'll use wrong packet structure)
            ]
            
            for ethertype in invalid_ethertypes:
                packet_config = PacketConfig(
                    ip_version=4,
                    dst_ip="192.168.1.1",
                    dst_port=80,
                    payload_size=64,
                    invalid_ethertype=ethertype
                )
                packet = generator.generate_packet(packet_config)
                
                self.log.info(f"Testing invalid EtherType: 0x{ethertype:04X}")
                
                await self.tb.send_packet(packet)
                # Invalid EtherType packets should be dropped
                self.tracker.add_packet_sent(len(packet), should_pass=False)
            
            # Send one valid packet for comparison
            valid_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
            valid_packet = generator.generate_packet(valid_config)
            
            await self.tb.send_packet(valid_packet)
            self.tracker.add_packet_sent(len(valid_packet), should_pass=True, rule_hit=0)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(len(invalid_ethertypes) + 1)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Invalid EtherType handling working correctly"
                self.log.info("TC-EDGE-003 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-EDGE-003 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-EDGE-003 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_edge_004(self, dut):
        """TC-EDGE-004: Truncated packets with early tlast."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-EDGE-004", "Truncated packets with early tlast")
        
        try:
            # Configure rule
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Test truncated packets at various points
            truncation_points = [10, 20, 30, 40, 50]  # Bytes
            
            for truncate_at in truncation_points:
                packet_config = PacketConfig(
                    ip_version=4,
                    dst_ip="192.168.1.1", 
                    dst_port=80,
                    payload_size=100,  # Large payload but truncated
                    truncate_bytes=100 - truncate_at  # Truncate to specific size
                )
                packet = generator.generate_packet(packet_config)
                
                self.log.info(f"Testing truncated packet: {len(packet)} bytes (truncated at {truncate_at})")
                
                await self.tb.send_packet(packet)
                # Truncated packets should be dropped (incomplete headers)
                self.tracker.add_packet_sent(len(packet), should_pass=False)
            
            # Send valid packet for comparison
            valid_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
            valid_packet = generator.generate_packet(valid_config)
            
            await self.tb.send_packet(valid_packet)
            self.tracker.add_packet_sent(len(valid_packet), should_pass=True, rule_hit=0)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(len(truncation_points) + 1)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Truncated packet handling working correctly"
                self.log.info("TC-EDGE-004 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-EDGE-004 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-EDGE-004 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_edge_005(self, dut):
        """TC-EDGE-005: Back-pressure handling."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-EDGE-005", "Back-pressure handling")
        
        try:
            # Configure rule
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Create back-pressure pattern (random ready)
            backpressure_pattern = [
                # Pattern: ready for 2 cycles, not ready for 3 cycles, repeat
                True, True, False, False, False,
                True, True, False, False, False,
                True, True, False, False, False,
            ]
            
            # Apply back-pressure
            await self.tb.apply_backpressure_pattern(backpressure_pattern)
            
            # Send packets during back-pressure
            packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
            packet = generator.generate_packet(packet_config)
            
            # Send multiple packets
            for i in range(5):
                await self.tb.send_packet(packet)
                self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                await Timer(100, units='ns')  # Space out packets
            
            # Remove back-pressure
            await self.tb.remove_backpressure()
            
            # Wait longer for packets to complete with back-pressure delays
            await self.checker.wait_for_statistics_update(5, timeout_cycles=5000)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Back-pressure handling working correctly"
                self.log.info("TC-EDGE-005 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-EDGE-005 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-EDGE-005 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result


# Cocotb test functions
@cocotb.test()
async def test_edge_001(dut):
    """Test malformed packets and error handling."""
    test_class = TestEdgeCases()
    result = await test_class.tc_edge_001(dut)
    assert result.passed, f"TC-EDGE-001 failed: {result.message}"


@cocotb.test()
async def test_edge_002(dut):
    """Test minimum and maximum packet sizes."""
    test_class = TestEdgeCases()
    result = await test_class.tc_edge_002(dut)
    assert result.passed, f"TC-EDGE-002 failed: {result.message}"


@cocotb.test()
async def test_edge_003(dut):
    """Test invalid EtherType handling."""
    test_class = TestEdgeCases()
    result = await test_class.tc_edge_003(dut)
    assert result.passed, f"TC-EDGE-003 failed: {result.message}"


@cocotb.test()
async def test_edge_004(dut):
    """Test truncated packets."""
    test_class = TestEdgeCases()
    result = await test_class.tc_edge_004(dut)
    assert result.passed, f"TC-EDGE-004 failed: {result.message}"


@cocotb.test()
async def test_edge_005(dut):
    """Test back-pressure handling."""
    test_class = TestEdgeCases()
    result = await test_class.tc_edge_005(dut)
    assert result.passed, f"TC-EDGE-005 failed: {result.message}"


# Test suite runner
@cocotb.test()
async def test_edge_cases_suite(dut):
    """Run complete edge cases test suite."""
    test_class = TestEdgeCases()
    
    # Run all edge case tests
    results = []
    results.append(await test_class.tc_edge_001(dut))
    results.append(await test_class.tc_edge_002(dut))
    results.append(await test_class.tc_edge_003(dut))
    results.append(await test_class.tc_edge_004(dut))
    results.append(await test_class.tc_edge_005(dut))
    
    # Print summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    test_class.log.info(f"\n{'='*60}")
    test_class.log.info(f"EDGE CASES TEST SUITE SUMMARY")
    test_class.log.info(f"{'='*60}")
    test_class.log.info(f"Tests Passed: {passed}/{total}")
    
    for result in results:
        status = "PASSED" if result.passed else "FAILED"
        test_class.log.info(f"{result.test_id:20} - {status:6} - {result.message}")
    
    # Overall result
    if passed == total:
        test_class.log.info("EDGE CASES TEST SUITE: ALL TESTS PASSED")
    else:
        test_class.log.error(f"EDGE CASES TEST SUITE: {total - passed} TESTS FAILED")
        assert False, f"Edge cases test suite failed: {passed}/{total} tests passed"
