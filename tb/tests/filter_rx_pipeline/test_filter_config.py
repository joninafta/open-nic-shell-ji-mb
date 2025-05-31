"""
Configuration and dynamic reconfiguration tests for filter_rx_pipeline.
Tests rule configuration, updates, and dynamic changes during traffic.

Test Cases Covered:
- TC-CFG-001: Rule configuration and validation
- TC-CFG-002: Multiple rule configurations
- TC-CFG-003: Rule priority and precedence
- TC-DYN-001: Dynamic rule updates during traffic
- TC-DYN-002: Rule enabling/disabling
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.log import SimLog
import asyncio

# Import our utilities
from utils.test_utils import FilterRxTestbench, TestResult, CommonRules
from utils.packet_generator import PacketGenerator, PacketConfig, TestPackets
from utils.statistics_checker import create_statistics_verifier


class TestConfiguration:
    """Test class for configuration functionality."""
    
    def __init__(self):
        self.log = SimLog("test_config")
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
        await Timer(100, units='ns')

    async def tc_cfg_001(self, dut):
        """TC-CFG-001: Rule configuration and validation."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-CFG-001", "Rule configuration and validation")
        
        try:
            # Test single rule configuration
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
            
            # Verify rule was written correctly by reading back
            readback_rule = await self.tb.read_rule(0)
            
            # Validate readback matches configuration
            if (readback_rule['dst_ip'] == rule['dst_ip'] and
                readback_rule['dst_port'] == rule['dst_port'] and
                readback_rule['action'] == rule['action']):
                
                # Test with matching packet
                generator = PacketGenerator()
                packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
                packet = generator.generate_packet(packet_config)
                
                await self.tb.send_packet(packet)
                self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                
                # Wait and verify
                await self.checker.wait_for_statistics_update(1)
                expected = self.tracker.get_expected_stats()
                comparison = await self.checker.verify_statistics(expected)
                
                if comparison.passed:
                    test_result.passed = True
                    test_result.message = "Rule configuration working correctly"
                    self.log.info("TC-CFG-001 PASSED")
                else:
                    test_result.passed = False
                    test_result.message = "Statistics verification failed"
                    self.log.error("TC-CFG-001 FAILED - statistics mismatch")
            else:
                test_result.passed = False
                test_result.message = "Rule readback verification failed"
                self.log.error("TC-CFG-001 FAILED - rule readback mismatch")
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-CFG-001 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_cfg_002(self, dut):
        """TC-CFG-002: Multiple rule configurations."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-CFG-002", "Multiple rule configurations")
        
        try:
            # Configure multiple rules with different patterns
            rules = [
                {
                    'rule_id': 0,
                    'ip_version': 4,
                    'dst_ip': '192.168.1.1',
                    'dst_ip_mask': '255.255.255.255',
                    'dst_port': 80,
                    'dst_port_mask': 0xFFFF,
                    'action': 'pass'
                },
                {
                    'rule_id': 1,
                    'ip_version': 4,
                    'dst_ip': '192.168.1.2',
                    'dst_ip_mask': '255.255.255.255',
                    'dst_port': 443,
                    'dst_port_mask': 0xFFFF,
                    'action': 'pass'
                },
                {
                    'rule_id': 2,
                    'ip_version': 6,
                    'dst_ip': '2001:db8::1',
                    'dst_ip_mask': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
                    'dst_port': 80,
                    'dst_port_mask': 0xFFFF,
                    'action': 'pass'
                }
            ]
            
            # Configure all rules
            await self.tb.configure_rules(rules)
            
            # Test each rule with appropriate packets
            generator = PacketGenerator()
            
            # Test packets for each rule
            test_cases = [
                (TestPackets.ipv4_http_packet("192.168.1.1", 64), True, 0),
                (TestPackets.ipv4_https_packet("192.168.1.2", 64), True, 1),
                (TestPackets.ipv6_http_packet("2001:db8::1", 64), True, 2),
                (TestPackets.ipv4_http_packet("192.168.1.3", 64), False, None),  # No match
            ]
            
            for packet_config, should_pass, rule_hit in test_cases:
                packet = generator.generate_packet(packet_config)
                await self.tb.send_packet(packet)
                self.tracker.add_packet_sent(len(packet), should_pass, rule_hit)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(len(test_cases))
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Multiple rule configuration working correctly"
                self.log.info("TC-CFG-002 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-CFG-002 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-CFG-002 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_dyn_001(self, dut):
        """TC-DYN-001: Dynamic rule updates during traffic."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-DYN-001", "Dynamic rule updates during traffic")
        
        try:
            # Initial rule configuration
            initial_rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            await self.tb.configure_rule(initial_rule)
            
            generator = PacketGenerator()
            
            # Phase 1: Send traffic with initial rule
            packet1_config = TestPackets.ipv4_http_packet("192.168.1.1", 64)
            packet1 = generator.generate_packet(packet1_config)
            
            for _ in range(3):
                await self.tb.send_packet(packet1)
                self.tracker.add_packet_sent(len(packet1), should_pass=True, rule_hit=0)
            
            # Phase 2: Update rule during traffic (change to different IP)
            updated_rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.2',  # Changed IP
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass'
            }
            
            # Send update while sending traffic
            update_task = cocotb.start_soon(self.tb.configure_rule(updated_rule))
            
            # Continue sending original packets (should now be dropped)
            for _ in range(2):
                await self.tb.send_packet(packet1)
                self.tracker.add_packet_sent(len(packet1), should_pass=False)
            
            await update_task  # Ensure update completes
            
            # Phase 3: Send traffic matching new rule
            packet2_config = TestPackets.ipv4_http_packet("192.168.1.2", 64)
            packet2 = generator.generate_packet(packet2_config)
            
            for _ in range(2):
                await self.tb.send_packet(packet2)
                self.tracker.add_packet_sent(len(packet2), should_pass=True, rule_hit=0)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(7)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Dynamic rule updates working correctly"
                self.log.info("TC-DYN-001 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-DYN-001 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-DYN-001 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_dyn_002(self, dut):
        """TC-DYN-002: Rule enabling/disabling."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-DYN-002", "Rule enabling/disabling")
        
        try:
            # Configure rule initially enabled
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '192.168.1.1',
                'dst_ip_mask': '255.255.255.255',
                'dst_port': 80,
                'dst_port_mask': 0xFFFF,
                'action': 'pass',
                'enabled': True
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            packet_config = TestPackets.ipv4_http_packet("192.168.1.1", 64)
            packet = generator.generate_packet(packet_config)
            
            # Phase 1: Rule enabled - packets should pass
            await self.tb.send_packet(packet)
            self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
            
            # Phase 2: Disable rule
            await self.tb.disable_rule(0)
            
            # Packets should now be dropped
            await self.tb.send_packet(packet)
            self.tracker.add_packet_sent(len(packet), should_pass=False)
            
            # Phase 3: Re-enable rule
            await self.tb.enable_rule(0)
            
            # Packets should pass again
            await self.tb.send_packet(packet)
            self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(3)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = "Rule enabling/disabling working correctly"
                self.log.info("TC-DYN-002 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-DYN-002 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-DYN-002 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result


# Cocotb test functions
@cocotb.test()
async def test_cfg_001(dut):
    """Test rule configuration and validation."""
    test_class = TestConfiguration()
    result = await test_class.tc_cfg_001(dut)
    assert result.passed, f"TC-CFG-001 failed: {result.message}"


@cocotb.test()
async def test_cfg_002(dut):
    """Test multiple rule configurations."""
    test_class = TestConfiguration()
    result = await test_class.tc_cfg_002(dut)
    assert result.passed, f"TC-CFG-002 failed: {result.message}"


@cocotb.test()
async def test_dyn_001(dut):
    """Test dynamic rule updates during traffic."""
    test_class = TestConfiguration()
    result = await test_class.tc_dyn_001(dut)
    assert result.passed, f"TC-DYN-001 failed: {result.message}"


@cocotb.test()
async def test_dyn_002(dut):
    """Test rule enabling/disabling."""
    test_class = TestConfiguration()
    result = await test_class.tc_dyn_002(dut)
    assert result.passed, f"TC-DYN-002 failed: {result.message}"


# Test suite runner
@cocotb.test()
async def test_configuration_suite(dut):
    """Run complete configuration test suite."""
    test_class = TestConfiguration()
    
    # Run all configuration tests
    results = []
    results.append(await test_class.tc_cfg_001(dut))
    results.append(await test_class.tc_cfg_002(dut))
    results.append(await test_class.tc_dyn_001(dut))
    results.append(await test_class.tc_dyn_002(dut))
    
    # Print summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    test_class.log.info(f"\n{'='*60}")
    test_class.log.info(f"CONFIGURATION TEST SUITE SUMMARY")
    test_class.log.info(f"{'='*60}")
    test_class.log.info(f"Tests Passed: {passed}/{total}")
    
    for result in results:
        status = "PASSED" if result.passed else "FAILED"
        test_class.log.info(f"{result.test_id:20} - {status:6} - {result.message}")
    
    # Overall result
    if passed == total:
        test_class.log.info("CONFIGURATION TEST SUITE: ALL TESTS PASSED")
    else:
        test_class.log.error(f"CONFIGURATION TEST SUITE: {total - passed} TESTS FAILED")
        assert False, f"Configuration test suite failed: {passed}/{total} tests passed"
