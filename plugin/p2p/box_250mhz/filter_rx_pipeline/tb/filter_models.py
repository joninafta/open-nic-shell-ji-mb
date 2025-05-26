"""
Filter Models for verifying filter_rx_pipeline behavior

Provides Python models of the filtering logic for verification
"""

import logging
from typing import Optional, Dict, Any
import ipaddress

logger = logging.getLogger(__name__)

class FilterRule:
    """Represents a single filtering rule"""
    
    def __init__(self, ipv4_addr: Optional[int] = None, 
                 ipv6_addr: Optional[int] = None,
                 port: Optional[int] = None):
        self.ipv4_addr = ipv4_addr or 0
        self.ipv6_addr = ipv6_addr or 0
        self.port = port or 0
        
    def __str__(self):
        parts = []
        if self.ipv4_addr != 0:
            try:
                ip_str = str(ipaddress.IPv4Address(self.ipv4_addr))
                parts.append(f"IPv4:{ip_str}")
            except:
                parts.append(f"IPv4:0x{self.ipv4_addr:08x}")
                
        if self.ipv6_addr != 0:
            try:
                ip_str = str(ipaddress.IPv6Address(self.ipv6_addr))
                parts.append(f"IPv6:{ip_str}")
            except:
                parts.append(f"IPv6:0x{self.ipv6_addr:032x}")
                
        if self.port != 0:
            parts.append(f"Port:{self.port}")
            
        if not parts:
            parts.append("WILDCARD")
            
        return f"Rule({', '.join(parts)})"

class PacketHeader:
    """Represents extracted packet headers"""
    
    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data
        self._parse_headers()
        
    def _parse_headers(self):
        """Parse packet headers from raw data"""
        if len(self.raw_data) < 14:
            raise ValueError("Packet too short for Ethernet header")
            
        # Parse Ethernet header
        self.eth_dst_mac = self.raw_data[0:6]
        self.eth_src_mac = self.raw_data[6:12]
        self.eth_type = int.from_bytes(self.raw_data[12:14], 'big')
        
        # Parse IP header based on EtherType
        if self.eth_type == 0x0800:  # IPv4
            self._parse_ipv4()
        elif self.eth_type == 0x86DD:  # IPv6
            self._parse_ipv6()
        else:
            self.is_ipv4 = False
            self.is_ipv6 = False
            self.src_ip = None
            self.dst_ip = None
            self.src_port = None
            self.dst_port = None
            return
            
    def _parse_ipv4(self):
        """Parse IPv4 header"""
        self.is_ipv4 = True
        self.is_ipv6 = False
        
        if len(self.raw_data) < 34:  # Eth + IPv4 + ports
            self.src_ip = None
            self.dst_ip = None
            self.src_port = None
            self.dst_port = None
            return
            
        # IPv4 addresses (bytes 26-29 and 30-33)
        self.src_ip = int.from_bytes(self.raw_data[26:30], 'big')
        self.dst_ip = int.from_bytes(self.raw_data[30:34], 'big')
        
        # Protocol field (byte 23)
        if len(self.raw_data) > 23:
            self.protocol = self.raw_data[23]
        else:
            self.protocol = 0
            
        # Port fields (bytes 34-37)
        if len(self.raw_data) >= 38:
            self.src_port = int.from_bytes(self.raw_data[34:36], 'big')
            self.dst_port = int.from_bytes(self.raw_data[36:38], 'big')
        else:
            self.src_port = None
            self.dst_port = None
            
    def _parse_ipv6(self):
        """Parse IPv6 header"""
        self.is_ipv4 = False
        self.is_ipv6 = True
        
        if len(self.raw_data) < 54:  # Eth + IPv6 + ports
            self.src_ip = None
            self.dst_ip = None
            self.src_port = None
            self.dst_port = None
            return
            
        # IPv6 addresses (bytes 22-37 and 38-53)
        self.src_ip = int.from_bytes(self.raw_data[22:38], 'big')
        self.dst_ip = int.from_bytes(self.raw_data[38:54], 'big')
        
        # Next header field (byte 20)
        if len(self.raw_data) > 20:
            self.next_header = self.raw_data[20]
        else:
            self.next_header = 0
            
        # Port fields (bytes 54-57)
        if len(self.raw_data) >= 58:
            self.src_port = int.from_bytes(self.raw_data[54:56], 'big')
            self.dst_port = int.from_bytes(self.raw_data[56:58], 'big')
        else:
            self.src_port = None
            self.dst_port = None
            
    def __str__(self):
        if self.is_ipv4:
            try:
                src_str = str(ipaddress.IPv4Address(self.src_ip))
                dst_str = str(ipaddress.IPv4Address(self.dst_ip))
            except:
                src_str = f"0x{self.src_ip:08x}"
                dst_str = f"0x{self.dst_ip:08x}"
            return f"IPv4 {src_str}:{self.src_port} -> {dst_str}:{self.dst_port}"
        elif self.is_ipv6:
            try:
                src_str = str(ipaddress.IPv6Address(self.src_ip))
                dst_str = str(ipaddress.IPv6Address(self.dst_ip))
            except:
                src_str = f"0x{self.src_ip:032x}"
                dst_str = f"0x{self.dst_ip:032x}"
            return f"IPv6 {src_str}:{self.src_port} -> {dst_str}:{self.dst_port}"
        else:
            return f"Unknown EtherType 0x{self.eth_type:04x}"

class FilterModel:
    """Python model of the filter_rx_pipeline filtering logic"""
    
    def __init__(self):
        self.rules = [FilterRule(), FilterRule()]  # Two rules
        self.counters = {
            'rule0_hit_count': 0,
            'rule1_hit_count': 0,
            'total_packets': 0,
            'dropped_packets': 0
        }
        
    def set_rule(self, rule_id: int, rule: FilterRule):
        """Set a filtering rule"""
        if rule_id not in [0, 1]:
            raise ValueError(f"Invalid rule ID: {rule_id}")
        self.rules[rule_id] = rule
        logger.info(f"Set rule {rule_id}: {rule}")
        
    def should_pass_packet(self, packet_data: bytes) -> tuple:
        """
        Determine if a packet should pass the filter
        Returns: (should_pass, rule_hit)
        """
        try:
            header = PacketHeader(packet_data)
        except Exception as e:
            logger.warning(f"Failed to parse packet: {e}")
            return False, 0
            
        logger.debug(f"Evaluating packet: {header}")
        
        # Check each rule
        rule0_match = self._rule_matches(self.rules[0], header)
        rule1_match = self._rule_matches(self.rules[1], header)
        
        # Update counters
        self.counters['total_packets'] += 1
        
        if rule0_match and rule1_match:
            # Both match - priority to rule 0
            self.counters['rule0_hit_count'] += 1
            logger.debug(f"Packet matches both rules - counted as rule 0")
            return True, 1
        elif rule0_match:
            self.counters['rule0_hit_count'] += 1
            logger.debug(f"Packet matches rule 0")
            return True, 1
        elif rule1_match:
            self.counters['rule1_hit_count'] += 1
            logger.debug(f"Packet matches rule 1")
            return True, 2
        else:
            self.counters['dropped_packets'] += 1
            logger.debug(f"Packet matches no rules - dropped")
            return False, 0
            
    def _rule_matches(self, rule: FilterRule, header: PacketHeader) -> bool:
        """Check if a packet header matches a rule"""
        
        if header.is_ipv4:
            # IPv4 matching
            ip_match = (rule.ipv4_addr == 0) or (header.src_ip == rule.ipv4_addr)
            port_match = (rule.port == 0) or (header.src_port == (rule.port & 0xFFFF))
            return ip_match or port_match
            
        elif header.is_ipv6:
            # IPv6 matching  
            ip_match = (rule.ipv6_addr == 0) or (header.src_ip == rule.ipv6_addr)
            port_match = (rule.port == 0) or (header.src_port == (rule.port & 0xFFFF))
            return ip_match or port_match
            
        else:
            # Unknown packet type - no match
            return False
            
    def get_counters(self) -> Dict[str, int]:
        """Get current counter values"""
        return self.counters.copy()
        
    def reset_counters(self):
        """Reset all counters to zero"""
        self.counters = {
            'rule0_hit_count': 0,
            'rule1_hit_count': 0,
            'total_packets': 0,
            'dropped_packets': 0
        }
        
    def __str__(self):
        lines = ["FilterModel:"]
        lines.append(f"  Rule 0: {self.rules[0]}")
        lines.append(f"  Rule 1: {self.rules[1]}")
        lines.append(f"  Counters: {self.counters}")
        return "\n".join(lines)

class FilterVerifier:
    """Utility class for verifying filter behavior"""
    
    def __init__(self, model: FilterModel):
        self.model = model
        
    def verify_packet_processing(self, input_packets: list, output_packets: list):
        """Verify that output packets match expected filtering results"""
        expected_outputs = []
        
        for packet in input_packets:
            should_pass, rule_hit = self.model.should_pass_packet(packet)
            if should_pass:
                expected_outputs.append(packet)
                
        # Compare lengths
        if len(output_packets) != len(expected_outputs):
            raise AssertionError(
                f"Expected {len(expected_outputs)} output packets, "
                f"got {len(output_packets)}"
            )
            
        # Compare packet contents
        for i, (expected, actual) in enumerate(zip(expected_outputs, output_packets)):
            if expected != actual:
                raise AssertionError(
                    f"Packet {i} mismatch:\n"
                    f"Expected: {expected.hex()}\n"
                    f"Actual:   {actual.hex()}"
                )
                
        logger.info(f"Verified {len(input_packets)} input packets -> {len(output_packets)} output packets")
        
    def verify_counters(self, dut_counters: Dict[str, int]):
        """Verify DUT counters match model counters"""
        model_counters = self.model.get_counters()
        
        for counter_name, expected_value in model_counters.items():
            if counter_name in dut_counters:
                actual_value = dut_counters[counter_name]
                if actual_value != expected_value:
                    raise AssertionError(
                        f"Counter {counter_name}: expected {expected_value}, "
                        f"got {actual_value}"
                    )
                    
        logger.info("Counter verification passed")
        
    def generate_test_report(self) -> str:
        """Generate a test report"""
        counters = self.model.get_counters()
        total = counters['total_packets']
        
        if total == 0:
            return "No packets processed"
            
        report = [
            "Filter Test Report:",
            f"  Total packets: {total}",
            f"  Rule 0 hits: {counters['rule0_hit_count']} ({100*counters['rule0_hit_count']/total:.1f}%)",
            f"  Rule 1 hits: {counters['rule1_hit_count']} ({100*counters['rule1_hit_count']/total:.1f}%)", 
            f"  Dropped: {counters['dropped_packets']} ({100*counters['dropped_packets']/total:.1f}%)",
        ]
        
        return "\n".join(report)
