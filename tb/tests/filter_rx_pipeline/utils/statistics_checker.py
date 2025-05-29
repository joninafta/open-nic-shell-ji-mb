"""
Statistics checker for filter_rx_pipeline verification.
Monitors and verifies statistics counters in the status register.
"""

import cocotb
from cocotb.triggers import RisingEdge
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time


@dataclass
class ExpectedStats:
    """Expected statistics values."""
    total_packets: int = 0
    dropped_packets: int = 0
    rule0_hit_count: int = 0
    rule1_hit_count: int = 0


@dataclass
class ActualStats:
    """Actual statistics values read from DUT."""
    total_packets: int = 0
    dropped_packets: int = 0
    rule0_hit_count: int = 0
    rule1_hit_count: int = 0
    timestamp: float = 0
    
    @classmethod
    def from_status_reg(cls, status_reg_value: int):
        """Parse statistics from status register value."""
        # Assuming status register layout (128 bits):
        # [31:0]   - total_packets
        # [63:32]  - dropped_packets  
        # [95:64]  - rule0_hit_count
        # [127:96] - rule1_hit_count
        
        total_packets = (status_reg_value >> 0) & 0xFFFFFFFF
        dropped_packets = (status_reg_value >> 32) & 0xFFFFFFFF
        rule0_hit_count = (status_reg_value >> 64) & 0xFFFFFFFF
        rule1_hit_count = (status_reg_value >> 96) & 0xFFFFFFFF
        
        return cls(
            total_packets=total_packets,
            dropped_packets=dropped_packets,
            rule0_hit_count=rule0_hit_count,
            rule1_hit_count=rule1_hit_count,
            timestamp=time.time()
        )


class StatisticsChecker:
    """Monitors and verifies filter_rx_pipeline statistics counters."""
    
    def __init__(self, dut, clock):
        """
        Initialize statistics checker.
        
        Args:
            dut: Device under test handle
            clock: Clock signal
        """
        self.dut = dut
        self.clock = clock
        
        # Statistics tracking
        self.expected = ExpectedStats()
        self.last_actual = ActualStats()
        self.history: list[ActualStats] = []
        
        # Verification results
        self.mismatches: list[str] = []
        self.last_check_passed = True
        
    async def read_current_stats(self) -> ActualStats:
        """Read current statistics from DUT."""
        await RisingEdge(self.clock)  # Ensure we read on clock edge
        
        # Read status register
        status_reg_value = int(self.dut.status_reg.value)
        actual = ActualStats.from_status_reg(status_reg_value)
        
        self.last_actual = actual
        self.history.append(actual)
        
        cocotb.log.debug(f"Read stats: total={actual.total_packets}, "
                        f"dropped={actual.dropped_packets}, "
                        f"rule0={actual.rule0_hit_count}, "
                        f"rule1={actual.rule1_hit_count}")
        
        return actual
        
    def expect_packet_sent(self, rule_hit: Optional[int] = None, dropped: bool = False):
        """Update expected statistics for a sent packet."""
        self.expected.total_packets += 1
        
        if dropped:
            self.expected.dropped_packets += 1
        elif rule_hit == 0:
            self.expected.rule0_hit_count += 1
        elif rule_hit == 1:
            self.expected.rule1_hit_count += 1
        else:
            # Packet processed but no rule hit specified - assume it was dropped
            self.expected.dropped_packets += 1
            
        cocotb.log.debug(f"Expected stats updated: total={self.expected.total_packets}, "
                        f"dropped={self.expected.dropped_packets}, "
                        f"rule0={self.expected.rule0_hit_count}, "
                        f"rule1={self.expected.rule1_hit_count}")
        
    async def verify_stats(self, tolerance_cycles: int = 10) -> bool:
        """
        Verify that actual statistics match expected values.
        
        Args:
            tolerance_cycles: Number of clock cycles to wait for counters to update
            
        Returns:
            True if stats match, False otherwise
        """
        # Wait a few cycles for counters to update
        for _ in range(tolerance_cycles):
            await RisingEdge(self.clock)
            
        actual = await self.read_current_stats()
        
        # Check each counter
        mismatches = []
        
        if actual.total_packets != self.expected.total_packets:
            mismatches.append(f"total_packets: expected {self.expected.total_packets}, "
                            f"actual {actual.total_packets}")
            
        if actual.dropped_packets != self.expected.dropped_packets:
            mismatches.append(f"dropped_packets: expected {self.expected.dropped_packets}, "
                            f"actual {actual.dropped_packets}")
            
        if actual.rule0_hit_count != self.expected.rule0_hit_count:
            mismatches.append(f"rule0_hit_count: expected {self.expected.rule0_hit_count}, "
                            f"actual {actual.rule0_hit_count}")
            
        if actual.rule1_hit_count != self.expected.rule1_hit_count:
            mismatches.append(f"rule1_hit_count: expected {self.expected.rule1_hit_count}, "
                            f"actual {actual.rule1_hit_count}")
            
        # Check consistency - total should equal sum of hits and drops
        expected_total = self.expected.rule0_hit_count + self.expected.rule1_hit_count + self.expected.dropped_packets
        if self.expected.total_packets != expected_total:
            mismatches.append(f"Expected statistics inconsistent: total={self.expected.total_packets}, "
                            f"but rule0+rule1+dropped={expected_total}")
            
        actual_total = actual.rule0_hit_count + actual.rule1_hit_count + actual.dropped_packets
        if actual.total_packets != actual_total:
            mismatches.append(f"Actual statistics inconsistent: total={actual.total_packets}, "
                            f"but rule0+rule1+dropped={actual_total}")
        
        # Store results
        self.mismatches.extend(mismatches)
        self.last_check_passed = len(mismatches) == 0
        
        # Log results
        if self.last_check_passed:
            cocotb.log.info("Statistics verification PASSED")
        else:
            cocotb.log.error("Statistics verification FAILED:")
            for mismatch in mismatches:
                cocotb.log.error(f"  - {mismatch}")
                
        return self.last_check_passed
        
    async def wait_for_stats_update(self, expected_total: int, timeout_cycles: int = 1000) -> bool:
        """
        Wait for statistics to reach expected total packet count.
        
        Args:
            expected_total: Expected total packet count
            timeout_cycles: Maximum cycles to wait
            
        Returns:
            True if target reached, False if timeout
        """
        for _ in range(timeout_cycles):
            actual = await self.read_current_stats()
            if actual.total_packets >= expected_total:
                return True
            await RisingEdge(self.clock)
            
        cocotb.log.warning(f"Timeout waiting for stats update: "
                          f"expected total >= {expected_total}, "
                          f"actual = {self.last_actual.total_packets}")
        return False
        
    def reset_expected_stats(self):
        """Reset expected statistics to zero."""
        self.expected = ExpectedStats()
        cocotb.log.debug("Expected statistics reset to zero")
        
    def clear_history(self):
        """Clear statistics history."""
        self.history.clear()
        self.mismatches.clear()
        
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get summary of verification results."""
        return {
            'last_check_passed': self.last_check_passed,
            'total_mismatches': len(self.mismatches),
            'mismatch_details': self.mismatches.copy(),
            'expected_stats': {
                'total_packets': self.expected.total_packets,
                'dropped_packets': self.expected.dropped_packets,
                'rule0_hit_count': self.expected.rule0_hit_count,
                'rule1_hit_count': self.expected.rule1_hit_count
            },
            'actual_stats': {
                'total_packets': self.last_actual.total_packets,
                'dropped_packets': self.last_actual.dropped_packets,
                'rule0_hit_count': self.last_actual.rule0_hit_count,
                'rule1_hit_count': self.last_actual.rule1_hit_count
            }
        }
        
    async def monitor_continuous_stats(self, duration_cycles: int, sample_interval: int = 100):
        """
        Continuously monitor statistics for a duration.
        
        Args:
            duration_cycles: How long to monitor
            sample_interval: How often to sample (in clock cycles)
        """
        cocotb.log.info(f"Starting continuous stats monitoring for {duration_cycles} cycles")
        
        samples = 0
        for cycle in range(0, duration_cycles, sample_interval):
            await self.read_current_stats()
            samples += 1
            
            # Wait for next sample interval
            for _ in range(min(sample_interval, duration_cycles - cycle)):
                await RisingEdge(self.clock)
                
        cocotb.log.info(f"Completed continuous monitoring: {samples} samples collected")
        
    def check_counter_overflow(self, counter_width: int = 32) -> list[str]:
        """
        Check for counter overflow conditions.
        
        Args:
            counter_width: Width of counters in bits
            
        Returns:
            List of overflow warnings
        """
        max_value = (1 << counter_width) - 1
        warnings = []
        
        if self.last_actual.total_packets >= max_value:
            warnings.append("total_packets counter at maximum value")
            
        if self.last_actual.dropped_packets >= max_value:
            warnings.append("dropped_packets counter at maximum value")
            
        if self.last_actual.rule0_hit_count >= max_value:
            warnings.append("rule0_hit_count counter at maximum value")
            
        if self.last_actual.rule1_hit_count >= max_value:
            warnings.append("rule1_hit_count counter at maximum value")
            
        for warning in warnings:
            cocotb.log.warning(f"Counter overflow: {warning}")
            
        return warnings
        
    async def verify_counter_increment(self, counter_name: str, expected_increment: int = 1) -> bool:
        """
        Verify that a specific counter increments by expected amount.
        
        Args:
            counter_name: Name of counter to check ('total', 'dropped', 'rule0', 'rule1')
            expected_increment: Expected increment value
            
        Returns:
            True if increment matches expectation
        """
        # Read initial value
        initial = await self.read_current_stats()
        
        # Wait a cycle and read again  
        await RisingEdge(self.clock)
        final = await self.read_current_stats()
        
        # Calculate actual increment
        if counter_name == 'total':
            actual_increment = final.total_packets - initial.total_packets
        elif counter_name == 'dropped':
            actual_increment = final.dropped_packets - initial.dropped_packets
        elif counter_name == 'rule0':
            actual_increment = final.rule0_hit_count - initial.rule0_hit_count
        elif counter_name == 'rule1':
            actual_increment = final.rule1_hit_count - initial.rule1_hit_count
        else:
            cocotb.log.error(f"Unknown counter name: {counter_name}")
            return False
            
        success = actual_increment == expected_increment
        
        if not success:
            cocotb.log.error(f"Counter {counter_name} increment mismatch: "
                           f"expected {expected_increment}, actual {actual_increment}")
        else:
            cocotb.log.debug(f"Counter {counter_name} increment verified: {actual_increment}")
            
        return success
