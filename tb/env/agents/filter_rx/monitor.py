"""
Filter RX specific monitor for OpenNIC testbench environment.
Monitors filter pipeline outputs and collects filtering statistics.
"""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from typing import Any, Optional, Dict, List
from dataclasses import dataclass

from ..base import Monitor, Transaction
from ..axi_stream import AxiStreamMonitor, AxiStreamTransaction
from .driver import FilterPacket


@dataclass
class FilterResult:
    """Result of filter operation on a packet."""
    packet: AxiStreamTransaction
    matched: bool
    rule_index: Optional[int] = None
    drop_reason: Optional[str] = None
    timestamp: float = 0.0


class FilterRxMonitor(Monitor):
    """
    Filter RX pipeline specific monitor.
    Observes filter outputs and collects statistics.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject,
                 output_monitor: AxiStreamMonitor,
                 filter_status_signals: Optional[Dict[str, cocotb.handle.HierarchyObject]] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize Filter RX monitor.
        
        Args:
            name: Monitor instance name
            clock: Clock signal
            output_monitor: AXI Stream monitor for output packets
            filter_status_signals: Optional filter status/debug signals
            config: Optional configuration
        """
        super().__init__(name, clock, config)
        self.output_monitor = output_monitor
        self.filter_status_signals = filter_status_signals or {}
        
        # Statistics
        self.packets_passed = 0
        self.packets_dropped = 0
        self.rule_hits: Dict[int, int] = {}
        
        # Recent filter results
        self._recent_results: List[FilterResult] = []
        self._max_recent_results = 1000
        
        # Connect to output monitor
        self.output_monitor.add_observer(self._on_output_packet)
        
    def _on_output_packet(self, transaction: AxiStreamTransaction) -> None:
        """Handle output packet from AXI Stream monitor."""
        result = FilterResult(
            packet=transaction,
            matched=True,  # If it's on output, it passed the filter
            timestamp=transaction.timestamp
        )
        
        self._add_result(result)
        self.packets_passed += 1
        
    def _add_result(self, result: FilterResult) -> None:
        """Add filter result to recent results list."""
        self._recent_results.append(result)
        
        # Maintain max size
        if len(self._recent_results) > self._max_recent_results:
            self._recent_results.pop(0)
            
        # Update rule statistics
        if result.rule_index is not None:
            if result.rule_index not in self.rule_hits:
                self.rule_hits[result.rule_index] = 0
            self.rule_hits[result.rule_index] += 1
            
    async def _monitor_interface(self) -> None:
        """Monitor filter-specific status signals."""
        await RisingEdge(self.clock)
        await ReadOnly()
        
        # Monitor filter status signals if available
        if 'drop_valid' in self.filter_status_signals:
            drop_valid = self.filter_status_signals['drop_valid']
            if drop_valid.value == 1:
                await self._handle_packet_drop()
                
    async def _handle_packet_drop(self) -> None:
        """Handle detection of a dropped packet."""
        self.packets_dropped += 1
        
        # Try to determine drop reason from status signals
        drop_reason = "unknown"
        if 'drop_reason' in self.filter_status_signals:
            reason_code = int(self.filter_status_signals['drop_reason'].value)
            drop_reason = self._decode_drop_reason(reason_code)
            
        # Create filter result for dropped packet
        timestamp = cocotb.utils.get_sim_time('ns')
        result = FilterResult(
            packet=None,  # We don't have the actual packet data
            matched=False,
            drop_reason=drop_reason,
            timestamp=timestamp
        )
        
        self._add_result(result)
        self.logger.debug(f"Packet dropped: {drop_reason}")
        
    def _decode_drop_reason(self, reason_code: int) -> str:
        """Decode drop reason from status signal."""
        reason_map = {
            0: "no_match",
            1: "invalid_packet",
            2: "buffer_full",
            3: "checksum_error",
            4: "size_error"
        }
        return reason_map.get(reason_code, f"unknown_code_{reason_code}")
        
    async def _get_last_transaction(self) -> FilterResult:
        """Get the most recent filter result."""
        if self._recent_results:
            return self._recent_results[-1]
        else:
            raise RuntimeError("No filter results observed yet")
            
    def get_filter_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive filter statistics.
        
        Returns:
            Dictionary with filter statistics
        """
        total_packets = self.packets_passed + self.packets_dropped
        pass_rate = (self.packets_passed / total_packets * 100) if total_packets > 0 else 0
        
        return {
            'total_packets': total_packets,
            'packets_passed': self.packets_passed,
            'packets_dropped': self.packets_dropped,
            'pass_rate_percent': pass_rate,
            'rule_hits': self.rule_hits.copy(),
            'recent_results_count': len(self._recent_results)
        }
        
    def get_recent_results(self, count: Optional[int] = None) -> List[FilterResult]:
        """
        Get recent filter results.
        
        Args:
            count: Number of recent results to return (None for all)
            
        Returns:
            List of recent filter results
        """
        if count is None:
            return self._recent_results.copy()
        else:
            return self._recent_results[-count:] if count <= len(self._recent_results) else self._recent_results.copy()
            
    def check_expected_drops(self, expected_drop_count: int, timeout_cycles: int = 1000) -> bool:
        """
        Check if expected number of drops occurred.
        
        Args:
            expected_drop_count: Expected number of dropped packets
            timeout_cycles: Maximum cycles to wait
            
        Returns:
            True if expected drops occurred
        """
        return self.packets_dropped >= expected_drop_count
        
    def check_expected_passes(self, expected_pass_count: int) -> bool:
        """
        Check if expected number of passes occurred.
        
        Args:
            expected_pass_count: Expected number of passed packets
            
        Returns:
            True if expected passes occurred
        """
        return self.packets_passed >= expected_pass_count
        
    def reset_statistics(self) -> None:
        """Reset all filter statistics."""
        self.packets_passed = 0
        self.packets_dropped = 0
        self.rule_hits.clear()
        self._recent_results.clear()
        self.logger.info("Filter statistics reset")
        
    def report_statistics(self) -> None:
        """Log comprehensive filter statistics."""
        stats = self.get_filter_statistics()
        
        self.logger.info(f"=== Filter Statistics for {self.name} ===")
        self.logger.info(f"Total packets: {stats['total_packets']}")
        self.logger.info(f"Packets passed: {stats['packets_passed']}")
        self.logger.info(f"Packets dropped: {stats['packets_dropped']}")
        self.logger.info(f"Pass rate: {stats['pass_rate_percent']:.1f}%")
        
        if stats['rule_hits']:
            self.logger.info("Rule hits:")
            for rule_index, hits in stats['rule_hits'].items():
                self.logger.info(f"  Rule {rule_index}: {hits} hits")
        else:
            self.logger.info("No rule hits recorded")
            
    async def wait_for_packets(self, expected_count: int, timeout_cycles: int = 1000) -> bool:
        """
        Wait for a specific number of output packets.
        
        Args:
            expected_count: Expected number of packets
            timeout_cycles: Maximum cycles to wait
            
        Returns:
            True if expected packets received
        """
        cycles_waited = 0
        
        while self.packets_passed < expected_count and cycles_waited < timeout_cycles:
            await RisingEdge(self.clock)
            cycles_waited += 1
            
        return self.packets_passed >= expected_count
