"""
Common test utilities for filter_rx_pipeline tests.
Provides shared functions for DUT control, configuration, and verification.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer
from cocotb.types import LogicArray
import logging

logger = logging.getLogger(__name__)


class FilterRxTestbench:
    """Main testbench class for filter_rx_pipeline tests."""
    
    def __init__(self, dut):
        self.dut = dut
        self.clock_period = 4  # 250MHz = 4ns period
        
        # Statistics tracking
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_dropped = 0
        
        # Expected results for verification
        self.expected_forwarded = []
        self.expected_dropped = []
        
    async def start_clock(self):
        """Start the clock."""
        clock = Clock(self.dut.aclk, self.clock_period, units="ns")
        cocotb.start_soon(clock.start())
        
    async def reset(self):
        """Reset the DUT."""
        logger.info("Resetting DUT...")
        
        # Initialize all input signals
        self.dut.s_axis_tvalid.value = 0
        self.dut.s_axis_tdata.value = 0
        self.dut.s_axis_tkeep.value = 0
        self.dut.s_axis_tlast.value = 0
        self.dut.s_axis_tuser.value = 0
        self.dut.m_axis_tready.value = 1  # Always ready for output
        
        # Clear configuration
        self.dut.cfg_reg.value = 0
        
        # Assert reset
        self.dut.aresetn.value = 0
        await ClockCycles(self.dut.aclk, 10)
        
        # Deassert reset
        self.dut.aresetn.value = 1
        await ClockCycles(self.dut.aclk, 5)
        
        logger.info("Reset complete")
        
    async def configure_rules(self, rules_config: dict):
        """
        Configure filter rules.
        
        Args:
            rules_config: Dictionary with rule configurations
                {
                    0: {"ipv4_addr": 0xC0A80101, "port": 80, "ipv6_addr": 0},
                    1: {"ipv4_addr": 0xC0A80102, "port": 443, "ipv6_addr": 0}
                }
        """
        logger.info(f"Configuring rules: {rules_config}")
        
        # Build configuration register value
        cfg_value = 0
        
        for rule_idx, rule_config in rules_config.items():
            if rule_idx >= 2:  # NUM_RULES = 2
                logger.warning(f"Rule index {rule_idx} exceeds NUM_RULES")
                continue
                
            # Each rule takes 192 bits (384 bits total for 2 rules)
            # Rule format: [IPv6_addr(128) | IPv4_addr(32) | Port(32)]
            rule_value = 0
            
            if "ipv6_addr" in rule_config:
                rule_value |= (rule_config["ipv6_addr"] & ((1 << 128) - 1)) << 64
                
            if "ipv4_addr" in rule_config:
                rule_value |= (rule_config["ipv4_addr"] & ((1 << 32) - 1)) << 32
                
            if "port" in rule_config:
                rule_value |= (rule_config["port"] & ((1 << 32) - 1))
                
            # Shift rule value to correct position in config register
            cfg_value |= rule_value << (rule_idx * 192)
            
        self.dut.cfg_reg.value = cfg_value
        await ClockCycles(self.dut.aclk, 1)
        
    async def send_axi_stream_packet(self, beats: list):
        """
        Send a packet as AXI Stream beats.
        
        Args:
            beats: List of (tdata, tkeep, tlast, tuser) tuples
        """
        for i, (tdata, tkeep, tlast, tuser) in enumerate(beats):
            # Set up the beat
            self.dut.s_axis_tvalid.value = 1
            self.dut.s_axis_tdata.value = tdata
            self.dut.s_axis_tkeep.value = tkeep
            self.dut.s_axis_tlast.value = tlast
            self.dut.s_axis_tuser.value = tuser
            
            # Wait for ready
            while True:
                await RisingEdge(self.dut.aclk)
                if self.dut.s_axis_tready.value == 1:
                    break
                    
            # If this was the last beat, clear signals
            if tlast:
                await RisingEdge(self.dut.aclk)
                self.dut.s_axis_tvalid.value = 0
                self.dut.s_axis_tdata.value = 0
                self.dut.s_axis_tkeep.value = 0
                self.dut.s_axis_tlast.value = 0
                self.dut.s_axis_tuser.value = 0
                break
                
        self.packets_sent += 1
        logger.debug(f"Sent packet {self.packets_sent} ({len(beats)} beats)")
        
    async def receive_axi_stream_packet(self, timeout_cycles: int = 100):
        """
        Receive a packet from AXI Stream output.
        
        Returns:
            List of (tdata, tkeep, tlast, tuser) tuples, or None if timeout
        """
        beats = []
        timeout_count = 0
        
        while timeout_count < timeout_cycles:
            await RisingEdge(self.dut.aclk)
            
            if self.dut.m_axis_tvalid.value == 1 and self.dut.m_axis_tready.value == 1:
                # Capture the beat
                tdata = int(self.dut.m_axis_tdata.value)
                tkeep = int(self.dut.m_axis_tkeep.value)
                tlast = bool(self.dut.m_axis_tlast.value)
                tuser = int(self.dut.m_axis_tuser.value)
                
                beats.append((tdata, tkeep, tlast, tuser))
                
                if tlast:
                    self.packets_received += 1
                    logger.debug(f"Received packet {self.packets_received} ({len(beats)} beats)")
                    return beats
                    
                timeout_count = 0  # Reset timeout on valid data
            else:
                timeout_count += 1
                
        # Timeout
        if beats:
            logger.warning(f"Timeout receiving packet, got {len(beats)} beats without tlast")
        return None
        
    async def send_packet_and_check_result(self, packet_beats: list, expect_forwarded: bool, 
                                         rule_hit: int = None, timeout_cycles: int = 100):
        """
        Send a packet and verify the expected result.
        
        Args:
            packet_beats: AXI Stream beats for the packet
            expect_forwarded: True if packet should be forwarded
            rule_hit: Expected rule hit index (0 or 1)
            timeout_cycles: Timeout for waiting for output
        """
        # Send the packet
        await self.send_axi_stream_packet(packet_beats)
        
        if expect_forwarded:
            # Wait for output packet
            received_beats = await self.receive_axi_stream_packet(timeout_cycles)
            
            if received_beats is None:
                raise AssertionError("Expected packet to be forwarded but none received")
                
            # Verify packet integrity (compare data)
            if len(received_beats) != len(packet_beats):
                raise AssertionError(f"Packet length mismatch: sent {len(packet_beats)}, received {len(received_beats)}")
                
            for i, ((sent_data, sent_keep, sent_last, _), (recv_data, recv_keep, recv_last, recv_user)) in enumerate(zip(packet_beats, received_beats)):
                if sent_data != recv_data:
                    raise AssertionError(f"Data mismatch at beat {i}: sent 0x{sent_data:x}, received 0x{recv_data:x}")
                if sent_keep != recv_keep:
                    raise AssertionError(f"Keep mismatch at beat {i}: sent 0x{sent_keep:x}, received 0x{recv_keep:x}")
                if sent_last != recv_last:
                    raise AssertionError(f"Last mismatch at beat {i}: sent {sent_last}, received {recv_last}")
                    
            logger.info("✅ Packet forwarded correctly")
            
        else:
            # Should not receive any packet - wait briefly then check
            await ClockCycles(self.dut.aclk, 20)
            
            # Check if any output is present
            if self.dut.m_axis_tvalid.value == 1:
                raise AssertionError("Expected packet to be dropped but output detected")
                
            logger.info("✅ Packet correctly dropped")
            
    async def wait_for_idle(self, cycles: int = 10):
        """Wait for the pipeline to become idle."""
        await ClockCycles(self.dut.aclk, cycles)
        
    def read_statistics(self) -> dict:
        """Read statistics counters from status register."""
        status_value = int(self.dut.status_reg.value)
        
        # Extract counter values (assuming each counter is 32 bits)
        stats = {
            "total_packets": (status_value >> 0) & 0xFFFFFFFF,
            "dropped_packets": (status_value >> 32) & 0xFFFFFFFF,
            "rule0_hit_count": (status_value >> 64) & 0xFFFFFFFF,
            "rule1_hit_count": (status_value >> 96) & 0xFFFFFFFF,
        }
        
        return stats
        
    def verify_statistics(self, expected_stats: dict):
        """Verify statistics counters match expected values."""
        actual_stats = self.read_statistics()
        
        for counter, expected_value in expected_stats.items():
            if counter not in actual_stats:
                raise AssertionError(f"Unknown counter: {counter}")
                
            actual_value = actual_stats[counter]
            if actual_value != expected_value:
                raise AssertionError(
                    f"Counter {counter} mismatch: expected {expected_value}, got {actual_value}"
                )
                
        logger.info(f"✅ Statistics verification passed: {actual_stats}")
        
    async def apply_backpressure_pattern(self, pattern: list):
        """
        Apply a back-pressure pattern to m_axis_tready.
        
        Args:
            pattern: List of boolean values for tready over time
        """
        for ready_val in pattern:
            self.dut.m_axis_tready.value = int(ready_val)
            await RisingEdge(self.dut.aclk)
            
        # Restore ready
        self.dut.m_axis_tready.value = 1


class TestResult:
    """Container for test results and verification."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = True
        self.errors = []
        self.warnings = []
        self.statistics = {}
        
    def add_error(self, message: str):
        """Add an error to the test result."""
        self.errors.append(message)
        self.passed = False
        logger.error(f"{self.test_name}: {message}")
        
    def add_warning(self, message: str):
        """Add a warning to the test result."""
        self.warnings.append(message)
        logger.warning(f"{self.test_name}: {message}")
        
    def add_statistics(self, stats: dict):
        """Add statistics to the test result."""
        self.statistics.update(stats)
        
    def summary(self) -> str:
        """Generate a summary of the test result."""
        status = "PASS" if self.passed else "FAIL"
        summary = f"{self.test_name}: {status}"
        
        if self.errors:
            summary += f" ({len(self.errors)} errors)"
        if self.warnings:
            summary += f" ({len(self.warnings)} warnings)"
            
        return summary


# Utility functions for common IP address conversions
def ipv4_str_to_int(ip_str: str) -> int:
    """Convert IPv4 string to integer."""
    parts = ip_str.split('.')
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def ipv6_str_to_int(ip_str: str) -> int:
    """Convert IPv6 string to 128-bit integer."""
    import ipaddress
    return int(ipaddress.IPv6Address(ip_str))


def create_rule_config(rule_idx: int, ipv4_addr: str = None, ipv6_addr: str = None, port: int = 0) -> dict:
    """Create a single rule configuration."""
    rule = {"port": port}
    
    if ipv4_addr:
        rule["ipv4_addr"] = ipv4_str_to_int(ipv4_addr)
    else:
        rule["ipv4_addr"] = 0
        
    if ipv6_addr:
        rule["ipv6_addr"] = ipv6_str_to_int(ipv6_addr)
    else:
        rule["ipv6_addr"] = 0
        
    return {rule_idx: rule}


# Common rule configurations for tests
class CommonRules:
    """Common rule configurations used across tests."""
    
    @staticmethod
    def ipv4_basic_rules():
        """Basic IPv4 rules for testing."""
        return {
            0: {"ipv4_addr": ipv4_str_to_int("192.168.1.1"), "port": 80, "ipv6_addr": 0},
            1: {"ipv4_addr": ipv4_str_to_int("192.168.1.2"), "port": 443, "ipv6_addr": 0}
        }
        
    @staticmethod
    def ipv6_basic_rules():
        """Basic IPv6 rules for testing."""
        return {
            0: {"ipv6_addr": ipv6_str_to_int("2001:db8::1"), "port": 80, "ipv4_addr": 0},
            1: {"ipv6_addr": ipv6_str_to_int("2001:db8::2"), "port": 443, "ipv4_addr": 0}
        }
        
    @staticmethod
    def mixed_protocol_rules():
        """Mixed IPv4/IPv6 rules."""
        return {
            0: {"ipv4_addr": ipv4_str_to_int("192.168.1.1"), "port": 80, "ipv6_addr": 0},
            1: {"ipv6_addr": ipv6_str_to_int("2001:db8::1"), "port": 443, "ipv4_addr": 0}
        }
        
    @staticmethod
    def priority_test_rules():
        """Rules for testing priority (overlapping rules)."""
        return {
            0: {"ipv4_addr": 0, "port": 80, "ipv6_addr": 0},  # Match any IP, port 80
            1: {"ipv4_addr": ipv4_str_to_int("192.168.1.1"), "port": 0, "ipv6_addr": 0}  # Match specific IP, any port
        }
        
    @staticmethod
    def wildcard_port_rules():
        """Rules with wildcard ports."""
        return {
            0: {"ipv4_addr": ipv4_str_to_int("192.168.1.1"), "port": 0, "ipv6_addr": 0},  # Any port
            1: {"ipv4_addr": ipv4_str_to_int("192.168.1.2"), "port": 443, "ipv6_addr": 0}  # Specific port
        }
