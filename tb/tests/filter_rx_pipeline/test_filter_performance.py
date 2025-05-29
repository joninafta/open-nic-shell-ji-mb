"""
Performance and throughput tests for filter_rx_pipeline.
Tests system performance under various traffic conditions.

Test Cases Covered:
- TC-PERF-001: Maximum throughput measurement
- TC-PERF-002: Burst traffic handling
- TC-PERF-003: Sustained traffic performance
- TC-PERF-004: Mixed packet size performance
- TC-PERF-005: Latency measurement
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.log import SimLog
import time
import asyncio

# Import our utilities
from utils.test_utils import FilterRxTestbench, TestResult, CommonRules
from utils.packet_generator import PacketGenerator, PacketConfig, TestPackets
from utils.statistics_checker import create_statistics_verifier


class TestPerformance:
    """Test class for performance and throughput testing."""
    
    def __init__(self):
        self.log = SimLog("test_perf")
        self.results = []
        self.clock_freq_mhz = 250.0  # 250 MHz system clock
    
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
        await Timer(500, units='ns')  # Longer delay for performance tests

    async def tc_perf_001(self, dut):
        """TC-PERF-001: Maximum throughput measurement."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-PERF-001", "Maximum throughput measurement")
        
        try:
            # Configure rule to pass all traffic (worst case for filtering)
            rule = {
                'rule_id': 0,
                'ip_version': 4,
                'dst_ip': '0.0.0.0',
                'dst_ip_mask': '0.0.0.0',  # Match all IPs
                'dst_port': 0,
                'dst_port_mask': 0x0000,  # Match all ports
                'action': 'pass'
            }
            await self.tb.configure_rule(rule)
            
            generator = PacketGenerator()
            
            # Test with 64-byte packets (worst case for throughput)
            packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=18)  # 64 bytes total
            packet = generator.generate_packet(packet_config)
            
            packet_count = 1000
            start_time = time.time()
            start_cycles = await self.tb.get_cycle_count()
            
            # Send packets back-to-back
            for i in range(packet_count):
                await self.tb.send_packet(packet, back_to_back=True)
                self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                
                # Progress indicator
                if (i + 1) % 100 == 0:
                    self.log.info(f"Sent {i + 1}/{packet_count} packets")
            
            # Wait for all packets to be processed
            await self.checker.wait_for_statistics_update(packet_count, timeout_cycles=10000)
            
            end_time = time.time()
            end_cycles = await self.tb.get_cycle_count()
            
            # Calculate performance metrics
            total_time = end_time - start_time
            total_cycles = end_cycles - start_cycles
            total_bytes = packet_count * len(packet)
            
            throughput_mbps = (total_bytes * 8) / (total_time * 1e6)
            throughput_gbps = throughput_mbps / 1000
            packets_per_second = packet_count / total_time
            
            # Theoretical maximum throughput (512-bit @ 250MHz = 128 Gbps)
            theoretical_max_gbps = (512 * self.clock_freq_mhz) / 1000
            efficiency_percent = (throughput_gbps / theoretical_max_gbps) * 100
            
            # Verify statistics
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            # Log performance results
            self.log.info(f"\n{'='*50}")
            self.log.info("PERFORMANCE MEASUREMENT RESULTS")
            self.log.info(f"{'='*50}")
            self.log.info(f"Packet Count: {packet_count}")
            self.log.info(f"Packet Size: {len(packet)} bytes")
            self.log.info(f"Total Bytes: {total_bytes}")
            self.log.info(f"Test Duration: {total_time:.3f} seconds")
            self.log.info(f"Total Cycles: {total_cycles}")
            self.log.info(f"Throughput: {throughput_gbps:.2f} Gbps ({throughput_mbps:.0f} Mbps)")
            self.log.info(f"Packets/sec: {packets_per_second:.0f}")
            self.log.info(f"Theoretical Max: {theoretical_max_gbps:.1f} Gbps")
            self.log.info(f"Efficiency: {efficiency_percent:.1f}%")
            
            # Performance criteria: Should achieve at least 50% of theoretical maximum
            min_required_gbps = theoretical_max_gbps * 0.5
            
            if comparison.passed and throughput_gbps >= min_required_gbps:
                test_result.passed = True
                test_result.message = f"Throughput: {throughput_gbps:.2f} Gbps (efficiency: {efficiency_percent:.1f}%)"
                self.log.info("TC-PERF-001 PASSED")
            else:
                test_result.passed = False
                if not comparison.passed:
                    test_result.message = f"Statistics verification failed"
                else:
                    test_result.message = f"Throughput {throughput_gbps:.2f} Gbps < required {min_required_gbps:.2f} Gbps"
                self.log.error("TC-PERF-001 FAILED")
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-PERF-001 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_perf_002(self, dut):
        """TC-PERF-002: Burst traffic handling."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-PERF-002", "Burst traffic handling")
        
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
            packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=64)
            packet = generator.generate_packet(packet_config)
            
            # Test burst patterns: burst size, idle cycles
            burst_patterns = [
                (10, 5),   # 10 packets, 5 idle cycles
                (50, 10),  # 50 packets, 10 idle cycles
                (100, 20), # 100 packets, 20 idle cycles
            ]
            
            total_packets = 0
            
            for burst_size, idle_cycles in burst_patterns:
                self.log.info(f"Testing burst: {burst_size} packets, {idle_cycles} idle cycles")
                
                # Send burst
                for i in range(burst_size):
                    await self.tb.send_packet(packet, back_to_back=True)
                    self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                    total_packets += 1
                
                # Idle period
                for _ in range(idle_cycles):
                    await RisingEdge(dut.clk)
                
                # Small delay between burst patterns
                await Timer(100, units='ns')
            
            # Wait for all packets to be processed
            await self.checker.wait_for_statistics_update(total_packets)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = f"Burst traffic handled correctly ({total_packets} packets)"
                self.log.info("TC-PERF-002 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-PERF-002 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-PERF-002 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_perf_003(self, dut):
        """TC-PERF-003: Sustained traffic performance."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-PERF-003", "Sustained traffic performance")
        
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
            packet_config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=128)
            packet = generator.generate_packet(packet_config)
            
            # Sustained traffic test - send packets for extended period
            test_duration_ms = 10  # 10 milliseconds of sustained traffic
            packet_interval_ns = 1000  # 1000 ns between packets (1MHz packet rate)
            
            start_time = time.time()
            packet_count = 0
            
            # Calculate expected number of packets
            expected_packets = int((test_duration_ms * 1e6) / packet_interval_ns)
            
            self.log.info(f"Starting sustained traffic test for {test_duration_ms}ms")
            self.log.info(f"Expected packets: ~{expected_packets}")
            
            # Send sustained traffic
            while (time.time() - start_time) < (test_duration_ms / 1000.0):
                await self.tb.send_packet(packet)
                self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                packet_count += 1
                
                # Wait for interval
                await Timer(packet_interval_ns, units='ns')
                
                # Progress indicator
                if packet_count % 100 == 0:
                    elapsed = time.time() - start_time
                    self.log.info(f"Sent {packet_count} packets in {elapsed*1000:.1f}ms")
            
            actual_duration = time.time() - start_time
            actual_packet_rate = packet_count / actual_duration
            
            self.log.info(f"Sustained traffic test completed:")
            self.log.info(f"Duration: {actual_duration*1000:.1f}ms")
            self.log.info(f"Packets sent: {packet_count}")
            self.log.info(f"Packet rate: {actual_packet_rate:.0f} packets/sec")
            
            # Wait for processing
            await self.checker.wait_for_statistics_update(packet_count)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = f"Sustained traffic handled correctly ({packet_count} packets, {actual_packet_rate:.0f} pps)"
                self.log.info("TC-PERF-003 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-PERF-003 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-PERF-003 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result

    async def tc_perf_004(self, dut):
        """TC-PERF-004: Mixed packet size performance."""
        await self.setup_test(dut)
        
        test_result = TestResult("TC-PERF-004", "Mixed packet size performance")
        
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
            
            # Mix of packet sizes representative of real traffic
            packet_sizes = [
                (64, 40),    # Small packets (40% of traffic)
                (256, 25),   # Medium packets (25%)
                (512, 20),   # Medium-large packets (20%)
                (1500, 15),  # Large packets (15%)
            ]
            
            # Create packet templates
            packet_templates = []
            for size, percentage in packet_sizes:
                payload_size = max(0, size - 54)  # Account for headers
                config = TestPackets.ipv4_http_packet("192.168.1.1", payload_size=payload_size)
                packet = generator.generate_packet(config)
                packet_templates.append((packet, percentage))
            
            # Send mixed traffic
            total_packets = 500
            start_time = time.time()
            
            for i in range(total_packets):
                # Select packet based on distribution
                rand_val = (i * 37) % 100  # Simple pseudo-random
                cumulative = 0
                
                for packet, percentage in packet_templates:
                    cumulative += percentage
                    if rand_val < cumulative:
                        await self.tb.send_packet(packet)
                        self.tracker.add_packet_sent(len(packet), should_pass=True, rule_hit=0)
                        break
                
                # Small random delay to simulate realistic traffic
                if i % 10 == 0:
                    await Timer(50, units='ns')
            
            end_time = time.time()
            test_duration = end_time - start_time
            
            # Calculate total bytes
            total_bytes = sum(self.tracker.packet_sizes)
            avg_packet_size = total_bytes / total_packets if total_packets > 0 else 0
            throughput_mbps = (total_bytes * 8) / (test_duration * 1e6)
            
            self.log.info(f"Mixed size traffic test results:")
            self.log.info(f"Total packets: {total_packets}")
            self.log.info(f"Total bytes: {total_bytes}")
            self.log.info(f"Average packet size: {avg_packet_size:.1f} bytes")
            self.log.info(f"Test duration: {test_duration:.3f} seconds")
            self.log.info(f"Throughput: {throughput_mbps:.1f} Mbps")
            
            # Wait and verify
            await self.checker.wait_for_statistics_update(total_packets)
            expected = self.tracker.get_expected_stats()
            comparison = await self.checker.verify_statistics(expected)
            
            if comparison.passed:
                test_result.passed = True
                test_result.message = f"Mixed traffic handled correctly ({throughput_mbps:.1f} Mbps, {avg_packet_size:.1f} avg bytes)"
                self.log.info("TC-PERF-004 PASSED")
            else:
                test_result.passed = False
                test_result.message = f"Statistics mismatch: {len(comparison.errors)} errors"
                self.log.error("TC-PERF-004 FAILED")
                self.checker.print_statistics_comparison(comparison)
                
        except Exception as e:
            test_result.passed = False
            test_result.message = f"Exception: {str(e)}"
            self.log.error(f"TC-PERF-004 FAILED with exception: {e}")
        
        finally:
            await self.teardown_test()
            self.results.append(test_result)
            return test_result


# Cocotb test functions
@cocotb.test()
async def test_perf_001(dut):
    """Test maximum throughput measurement."""
    test_class = TestPerformance()
    result = await test_class.tc_perf_001(dut)
    assert result.passed, f"TC-PERF-001 failed: {result.message}"


@cocotb.test()
async def test_perf_002(dut):
    """Test burst traffic handling."""
    test_class = TestPerformance()
    result = await test_class.tc_perf_002(dut)
    assert result.passed, f"TC-PERF-002 failed: {result.message}"


@cocotb.test()
async def test_perf_003(dut):
    """Test sustained traffic performance."""
    test_class = TestPerformance()
    result = await test_class.tc_perf_003(dut)
    assert result.passed, f"TC-PERF-003 failed: {result.message}"


@cocotb.test()
async def test_perf_004(dut):
    """Test mixed packet size performance."""
    test_class = TestPerformance()
    result = await test_class.tc_perf_004(dut)
    assert result.passed, f"TC-PERF-004 failed: {result.message}"


# Test suite runner
@cocotb.test()
async def test_performance_suite(dut):
    """Run complete performance test suite."""
    test_class = TestPerformance()
    
    # Run all performance tests
    results = []
    results.append(await test_class.tc_perf_001(dut))
    results.append(await test_class.tc_perf_002(dut))
    results.append(await test_class.tc_perf_003(dut))
    results.append(await test_class.tc_perf_004(dut))
    
    # Print summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    test_class.log.info(f"\n{'='*60}")
    test_class.log.info(f"PERFORMANCE TEST SUITE SUMMARY")
    test_class.log.info(f"{'='*60}")
    test_class.log.info(f"Tests Passed: {passed}/{total}")
    
    for result in results:
        status = "PASSED" if result.passed else "FAILED"
        test_class.log.info(f"{result.test_id:20} - {status:6} - {result.message}")
    
    # Overall result
    if passed == total:
        test_class.log.info("PERFORMANCE TEST SUITE: ALL TESTS PASSED")
    else:
        test_class.log.error(f"PERFORMANCE TEST SUITE: {total - passed} TESTS FAILED")
        assert False, f"Performance test suite failed: {passed}/{total} tests passed"
