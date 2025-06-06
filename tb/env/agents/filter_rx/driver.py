"""
Filter RX specific driver for OpenNIC testbench environment.
Handles filter configuration and packet generation for filter_rx_pipeline testing.
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from typing import Any, Optional, Dict, List, Tuple
import random

from ...base import Driver
from ..axi_stream import AxiStreamDriver, AxiStreamTransaction


class FilterPacket:
    """Packet with filter-specific metadata."""
    
    def __init__(self, data: List[int], src_mac: int = 0, dst_mac: int = 0, 
                 eth_type: int = 0x0800, src_ip: int = 0, dst_ip: int = 0,
                 src_port: int = 0, dst_port: int = 0, protocol: int = 0x11):
        """
        Initialize filter packet.
        
        Args:
            data: Raw packet data
            src_mac: Source MAC address (48-bit)
            dst_mac: Destination MAC address (48-bit)
            eth_type: Ethernet type field
            src_ip: Source IP address (32-bit)
            dst_ip: Destination IP address (32-bit)
            src_port: Source port (16-bit)
            dst_port: Destination port (16-bit)
            protocol: IP protocol field
        """
        self.data = data
        self.src_mac = src_mac
        self.dst_mac = dst_mac
        self.eth_type = eth_type
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.protocol = protocol
        
    def to_axi_stream_transaction(self, user: int = 0) -> AxiStreamTransaction:
        """Convert to AXI Stream transaction."""
        return AxiStreamTransaction(
            data=self.data,
            last=True,
            user=user
        )
        
    def matches_filter(self, filter_rule: Dict[str, Any]) -> bool:
        """
        Check if packet matches a filter rule.
        
        Args:
            filter_rule: Filter rule dictionary
            
        Returns:
            True if packet matches the rule
        """
        # Check each field in the filter rule
        if 'src_mac' in filter_rule and self.src_mac != filter_rule['src_mac']:
            return False
        if 'dst_mac' in filter_rule and self.dst_mac != filter_rule['dst_mac']:
            return False
        if 'eth_type' in filter_rule and self.eth_type != filter_rule['eth_type']:
            return False
        if 'src_ip' in filter_rule and self.src_ip != filter_rule['src_ip']:
            return False
        if 'dst_ip' in filter_rule and self.dst_ip != filter_rule['dst_ip']:
            return False
        if 'src_port' in filter_rule and self.src_port != filter_rule['src_port']:
            return False
        if 'dst_port' in filter_rule and self.dst_port != filter_rule['dst_port']:
            return False
        if 'protocol' in filter_rule and self.protocol != filter_rule['protocol']:
            return False
            
        return True


class FilterRxDriver(Driver):
    """
    Filter RX pipeline specific driver.
    Manages filter configuration and generates test packets.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject,
                 axi_stream_driver: AxiStreamDriver,
                 config_signals: Optional[Dict[str, cocotb.handle.HierarchyObject]] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize Filter RX driver.
        
        Args:
            name: Driver instance name
            clock: Clock signal
            axi_stream_driver: AXI Stream driver for packet injection
            config_signals: Optional configuration interface signals
            config: Optional configuration
        """
        super().__init__(name, clock, config)
        self.axi_stream_driver = axi_stream_driver
        self.config_signals = config_signals or {}
        
        # Filter rule storage
        self.filter_rules: List[Dict[str, Any]] = []
        
    async def configure_filter_rule(self, rule_index: int, rule: Dict[str, Any]) -> None:
        """
        Configure a filter rule.
        
        Args:
            rule_index: Index of the rule to configure
            rule: Filter rule dictionary
        """
        # Store rule locally
        while len(self.filter_rules) <= rule_index:
            self.filter_rules.append({})
        self.filter_rules[rule_index] = rule.copy()
        
        self.logger.info(f"Configured filter rule {rule_index}: {rule}")
        
        # If we have config signals, write to hardware
        if self.config_signals:
            await self._write_hardware_rule(rule_index, rule)
            
    async def _write_hardware_rule(self, rule_index: int, rule: Dict[str, Any]) -> None:
        """Write filter rule to hardware configuration interface."""
        # This would implement the actual hardware configuration protocol
        # For now, just log the operation
        self.logger.debug(f"Writing rule {rule_index} to hardware: {rule}")
        await self.wait_clock_cycles(1)
        
    async def send_filter_packet(self, packet: FilterPacket) -> None:
        """
        Send a packet through the filter pipeline.
        
        Args:
            packet: Packet to send
        """
        axi_txn = packet.to_axi_stream_transaction()
        await self.axi_stream_driver.send_transaction(axi_txn)
        self._transactions_sent += 1
        
    async def send_transaction(self, transaction: Any) -> None:
        """Send transaction - delegates to appropriate method."""
        if isinstance(transaction, FilterPacket):
            await self.send_filter_packet(transaction)
        elif isinstance(transaction, AxiStreamTransaction):
            await self.axi_stream_driver.send_transaction(transaction)
        else:
            raise TypeError(f"Unsupported transaction type: {type(transaction)}")
            
    def generate_matching_packet(self, rule_index: int, size: int = 64) -> FilterPacket:
        """
        Generate a packet that matches a specific filter rule.
        
        Args:
            rule_index: Index of the rule to match
            size: Packet size in bytes
            
        Returns:
            Packet that matches the rule
        """
        if rule_index >= len(self.filter_rules):
            raise IndexError(f"Filter rule {rule_index} not configured")
            
        rule = self.filter_rules[rule_index]
        
        # Create packet with rule values
        packet = FilterPacket(
            data=[random.randint(0, 255) for _ in range(size)],
            src_mac=rule.get('src_mac', random.randint(0, 0xFFFFFFFFFFFF)),
            dst_mac=rule.get('dst_mac', random.randint(0, 0xFFFFFFFFFFFF)),
            eth_type=rule.get('eth_type', 0x0800),
            src_ip=rule.get('src_ip', random.randint(0, 0xFFFFFFFF)),
            dst_ip=rule.get('dst_ip', random.randint(0, 0xFFFFFFFF)),
            src_port=rule.get('src_port', random.randint(0, 0xFFFF)),
            dst_port=rule.get('dst_port', random.randint(0, 0xFFFF)),
            protocol=rule.get('protocol', 0x11)
        )
        
        return packet
        
    def generate_non_matching_packet(self, size: int = 64) -> FilterPacket:
        """
        Generate a packet that doesn't match any configured rules.
        
        Args:
            size: Packet size in bytes
            
        Returns:
            Packet that doesn't match any rules
        """
        max_attempts = 100
        
        for _ in range(max_attempts):
            packet = FilterPacket(
                data=[random.randint(0, 255) for _ in range(size)],
                src_mac=random.randint(0, 0xFFFFFFFFFFFF),
                dst_mac=random.randint(0, 0xFFFFFFFFFFFF),
                eth_type=random.choice([0x0800, 0x86DD, 0x0806]),
                src_ip=random.randint(0, 0xFFFFFFFF),
                dst_ip=random.randint(0, 0xFFFFFFFF),
                src_port=random.randint(0, 0xFFFF),
                dst_port=random.randint(0, 0xFFFF),
                protocol=random.choice([0x06, 0x11, 0x01])
            )
            
            # Check if packet matches any rule
            matches_any = any(packet.matches_filter(rule) for rule in self.filter_rules)
            
            if not matches_any:
                return packet
                
        # If we can't generate a non-matching packet, create one with impossible values
        return FilterPacket(
            data=[0xFF] * size,
            src_mac=0xFFFFFFFFFFFF,
            dst_mac=0xFFFFFFFFFFFF,
            eth_type=0xFFFF,
            src_ip=0xFFFFFFFF,
            dst_ip=0xFFFFFFFF,
            src_port=0xFFFF,
            dst_port=0xFFFF,
            protocol=0xFF
        )
        
    async def send_test_sequence(self, num_matching: int = 10, num_non_matching: int = 5) -> Tuple[List[FilterPacket], List[FilterPacket]]:
        """
        Send a sequence of test packets.
        
        Args:
            num_matching: Number of matching packets per rule
            num_non_matching: Number of non-matching packets
            
        Returns:
            Tuple of (matching_packets, non_matching_packets)
        """
        matching_packets = []
        non_matching_packets = []
        
        # Send matching packets for each configured rule
        for rule_index in range(len(self.filter_rules)):
            for _ in range(num_matching):
                packet = self.generate_matching_packet(rule_index)
                await self.send_filter_packet(packet)
                matching_packets.append(packet)
                
        # Send non-matching packets
        for _ in range(num_non_matching):
            packet = self.generate_non_matching_packet()
            await self.send_filter_packet(packet)
            non_matching_packets.append(packet)
            
        return matching_packets, non_matching_packets
        
    async def _reset_signals(self) -> None:
        """Reset filter-specific signals."""
        # Reset AXI Stream driver
        await self.axi_stream_driver.reset_interface()
        
        # Reset any filter configuration signals
        for signal in self.config_signals.values():
            signal.value = 0
