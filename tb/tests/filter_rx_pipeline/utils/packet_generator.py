"""
Packet generation utilities for filter_rx_pipeline tests.
Creates Ethernet/IPv4/IPv6 packets with proper AXI Stream formatting using Scapy.
"""

import random
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass

try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    from scapy.layers.l2 import Ether
except ImportError:
    print("Warning: Scapy not found. Install with: pip install scapy")
    raise


@dataclass
class PacketConfig:
    """Configuration for packet generation."""
    eth_dst: str = "00:11:22:33:44:55"
    eth_src: str = "aa:bb:cc:dd:ee:ff"
    ip_version: int = 4
    dst_ip: str = "192.168.1.1"
    src_ip: str = "10.0.0.1"
    dst_port: int = 80
    src_port: int = 12345
    protocol: str = "TCP"  # "TCP" or "UDP"
    payload_size: int = 0
    payload_pattern: str = "increment"  # "increment", "random", "fixed", "custom"
    custom_payload: Optional[bytes] = None
    # Additional fields for testing edge cases
    invalid_ethertype: Optional[int] = None
    truncate_at: Optional[int] = None  # Truncate packet at this byte position


class PacketGenerator:
    """Generates network packets for testing using Scapy."""
    
    def __init__(self):
        self.sequence_number = 0
        
    def generate_payload(self, config: PacketConfig) -> bytes:
        """Generate packet payload."""
        if config.payload_size == 0:
            return b''
            
        if config.custom_payload:
            return config.custom_payload[:config.payload_size]
            
        if config.payload_pattern == "increment":
            return bytes(i % 256 for i in range(config.payload_size))
        elif config.payload_pattern == "random":
            return bytes(random.randint(0, 255) for _ in range(config.payload_size))
        elif config.payload_pattern == "fixed":
            return b'\xAA' * config.payload_size
        else:
            return b'\x00' * config.payload_size
            
    def generate_packet(self, config: PacketConfig) -> bytes:
        """Generate complete packet using Scapy."""
        # Generate payload
        payload = self.generate_payload(config)
        
        # Create Ethernet header
        eth = Ether(dst=config.eth_dst, src=config.eth_src)
        
        # Handle invalid EtherType for malformed packet testing
        if config.invalid_ethertype:
            eth.type = config.invalid_ethertype
        
        # Create IP layer
        if config.ip_version == 4:
            ip = IP(dst=config.dst_ip, src=config.src_ip)
        else:  # IPv6
            ip = IPv6(dst=config.dst_ip, src=config.src_ip)
            
        # Create transport layer
        if config.protocol.upper() == "TCP":
            transport = TCP(dport=config.dst_port, sport=config.src_port, seq=self.sequence_number)
            self.sequence_number += len(payload) + 1
        else:  # UDP
            transport = UDP(dport=config.dst_port, sport=config.src_port)
            
        # Combine layers
        if config.invalid_ethertype:
            # For malformed packets, just use raw ethernet frame
            packet = eth / Raw(payload)
        else:
            packet = eth / ip / transport / Raw(payload)
            
        # Convert to bytes
        packet_bytes = bytes(packet)
        
        # Handle truncation for malformed packet testing
        if config.truncate_at:
            packet_bytes = packet_bytes[:config.truncate_at]
        
        # Pad to minimum Ethernet frame size (64 bytes) if not truncated
        if not config.truncate_at and len(packet_bytes) < 64:
            packet_bytes += b'\x00' * (64 - len(packet_bytes))
            
        return packet_bytes
        
    def packet_to_axi_stream_beats(self, packet: bytes, data_width: int = 512) -> List[Tuple[int, int, bool, int]]:
        """
        Convert packet to AXI Stream beats.
        
        Args:
            packet: Raw packet bytes
            data_width: AXI Stream data width in bits
            
        Returns:
            List of (tdata, tkeep, tlast, tuser) tuples
        """
        bytes_per_beat = data_width // 8
        beats = []
        
        for i in range(0, len(packet), bytes_per_beat):
            beat_data = packet[i:i + bytes_per_beat]
            
            # Pad beat to full width
            if len(beat_data) < bytes_per_beat:
                beat_data += b'\x00' * (bytes_per_beat - len(beat_data))
                
            # Convert to integer (little-endian for AXI Stream)
            tdata = int.from_bytes(beat_data, byteorder='little')
            
            # Generate tkeep - 1 bit per byte, only for valid bytes
            valid_bytes = min(len(packet) - i, bytes_per_beat)
            tkeep = (1 << valid_bytes) - 1
            
            # tlast on final beat
            tlast = (i + bytes_per_beat >= len(packet))
            
            # tuser - can be used for metadata (keeping as 0 for now)
            tuser = 0
            
            beats.append((tdata, tkeep, tlast, tuser))
            
        return beats
        
    def create_packet_summary(self, config: PacketConfig) -> str:
        """Create a human-readable summary of the packet configuration."""
        protocol_str = f"{config.protocol}:{config.dst_port}"
        if config.ip_version == 4:
            return f"IPv4 {config.dst_ip}:{config.dst_port} ← {config.src_ip}:{config.src_port} ({config.protocol})"
        else:
            return f"IPv6 {config.dst_ip}:{config.dst_port} ← {config.src_ip}:{config.src_port} ({config.protocol})"


# Predefined packet configurations for common test scenarios
class TestPackets:
    """Predefined packet configurations for testing."""
    
    @staticmethod
    def ipv4_http_packet(dst_ip: str = "192.168.1.1", payload_size: int = 0) -> PacketConfig:
        """IPv4 HTTP packet configuration."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=80,
            src_port=12345,
            protocol="TCP",
            payload_size=payload_size
        )
        
    @staticmethod
    def ipv4_https_packet(dst_ip: str = "192.168.1.2", payload_size: int = 64) -> PacketConfig:
        """IPv4 HTTPS packet configuration."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=443,
            src_port=54321,
            protocol="TCP",
            payload_size=payload_size
        )
        
    @staticmethod
    def ipv6_http_packet(dst_ip: str = "2001:db8::1", payload_size: int = 0) -> PacketConfig:
        """IPv6 HTTP packet configuration."""
        return PacketConfig(
            ip_version=6,
            dst_ip=dst_ip,
            dst_port=80,
            src_port=12345,
            protocol="TCP",
            payload_size=payload_size
        )
        
    @staticmethod
    def ipv6_https_packet(dst_ip: str = "2001:db8::2", payload_size: int = 1436) -> PacketConfig:
        """IPv6 HTTPS packet configuration."""
        return PacketConfig(
            ip_version=6,
            dst_ip=dst_ip,
            dst_port=443,
            src_port=12345,
            protocol="TCP",
            payload_size=payload_size
        )
        
    @staticmethod
    def malformed_ethertype_packet(payload_size: int = 32) -> PacketConfig:
        """Malformed packet with invalid EtherType."""
        return PacketConfig(
            ip_version=4,
            dst_ip="192.168.1.1",
            payload_size=payload_size,
            invalid_ethertype=0x1234  # Invalid EtherType
        )
        
    @staticmethod
    def truncated_packet(dst_ip: str = "192.168.1.1", truncate_at: int = 30) -> PacketConfig:
        """Truncated packet for testing early tlast."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=80,
            payload_size=100,
            truncate_at=truncate_at
        )
        
    @staticmethod
    def jumbo_frame_packet(dst_ip: str = "192.168.1.1") -> PacketConfig:
        """9KB jumbo frame packet."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=80,
            payload_size=9000
        )
        
    @staticmethod
    def wildcard_port_test_packets(dst_ip: str = "192.168.1.1") -> List[PacketConfig]:
        """Multiple packets with different ports for wildcard testing."""
        ports = [80, 443, 8080, 65535, 1, 22]
        return [
            PacketConfig(
                ip_version=4,
                dst_ip=dst_ip,
                dst_port=port,
                src_port=12345,
                protocol="TCP",
                payload_size=0
            )
            for port in ports
        ]


class IPv4PacketTemplate:
    """Template for IPv4 packet generation."""
    
    @staticmethod
    def http_packet(dst_ip: str = "192.168.1.1", payload_size: int = 0) -> PacketConfig:
        """Generate IPv4 HTTP packet configuration."""
        return TestPackets.ipv4_http_packet(dst_ip, payload_size)
    
    @staticmethod 
    def https_packet(dst_ip: str = "192.168.1.2", payload_size: int = 64) -> PacketConfig:
        """Generate IPv4 HTTPS packet configuration."""
        return TestPackets.ipv4_https_packet(dst_ip, payload_size)
    
    @staticmethod
    def udp_packet(dst_ip: str = "192.168.1.1", dst_port: int = 53, payload_size: int = 32) -> PacketConfig:
        """Generate IPv4 UDP packet configuration."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="UDP",
            payload_size=payload_size
        )


class IPv6PacketTemplate:
    """Template for IPv6 packet generation."""
    
    @staticmethod
    def http_packet(dst_ip: str = "2001:db8::1", payload_size: int = 0) -> PacketConfig:
        """Generate IPv6 HTTP packet configuration."""
        return TestPackets.ipv6_http_packet(dst_ip, payload_size)
    
    @staticmethod
    def https_packet(dst_ip: str = "2001:db8::2", payload_size: int = 1436) -> PacketConfig:
        """Generate IPv6 HTTPS packet configuration."""
        return TestPackets.ipv6_https_packet(dst_ip, payload_size)
    
    @staticmethod
    def udp_packet(dst_ip: str = "2001:db8::1", dst_port: int = 53, payload_size: int = 32) -> PacketConfig:
        """Generate IPv6 UDP packet configuration."""
        return PacketConfig(
            ip_version=6,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="UDP",
            payload_size=payload_size
        )


class UDPPacketTemplate:
    """Template for UDP packet generation (IPv4/IPv6)."""
    
    @staticmethod
    def ipv4_packet(dst_ip: str = "192.168.1.1", dst_port: int = 53, payload_size: int = 32) -> PacketConfig:
        """Generate IPv4 UDP packet configuration."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="UDP",
            payload_size=payload_size
        )
    
    @staticmethod
    def ipv6_packet(dst_ip: str = "2001:db8::1", dst_port: int = 53, payload_size: int = 32) -> PacketConfig:
        """Generate IPv6 UDP packet configuration."""
        return PacketConfig(
            ip_version=6,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="UDP",
            payload_size=payload_size
        )


class TCPPacketTemplate:
    """Template for TCP packet generation (IPv4/IPv6)."""
    
    @staticmethod
    def ipv4_packet(dst_ip: str = "192.168.1.1", dst_port: int = 80, payload_size: int = 0) -> PacketConfig:
        """Generate IPv4 TCP packet configuration."""
        return PacketConfig(
            ip_version=4,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="TCP",
            payload_size=payload_size
        )
    
    @staticmethod
    def ipv6_packet(dst_ip: str = "2001:db8::1", dst_port: int = 80, payload_size: int = 0) -> PacketConfig:
        """Generate IPv6 TCP packet configuration."""
        return PacketConfig(
            ip_version=6,
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=12345,
            protocol="TCP",
            payload_size=payload_size
        )


def create_packet_sequence(configs: List[PacketConfig]) -> List[bytes]:
    """Create a sequence of packets from configurations."""
    generator = PacketGenerator()
    return [generator.generate_packet(config) for config in configs]


def create_axi_stream_sequence(packets: List[bytes], data_width: int = 512) -> List[List[Tuple[int, int, bool, int]]]:
    """Convert packet sequence to AXI Stream beat sequences."""
    generator = PacketGenerator()
    return [generator.packet_to_axi_stream_beats(packet, data_width) for packet in packets]


def print_packet_info(packet_bytes: bytes, description: str = ""):
    """Debug utility to print packet information using Scapy."""
    try:
        packet = Ether(packet_bytes)
        print(f"\n{description}")
        print(f"Packet size: {len(packet_bytes)} bytes")
        packet.show()
    except Exception as e:
        print(f"Error parsing packet: {e}")
        print(f"Raw bytes: {packet_bytes.hex()}")


# Utility functions for common test patterns
def create_test_scenario_packets() -> dict:
    """Create packets for various test scenarios."""
    scenarios = {}
    
    # Basic IPv4 filtering test packets
    scenarios['ipv4_basic'] = [
        TestPackets.ipv4_http_packet("192.168.1.1"),      # Should match Rule 0
        TestPackets.ipv4_https_packet("192.168.1.2"),     # Should match Rule 1  
        TestPackets.ipv4_http_packet("192.168.1.3"),      # Should not match
        PacketConfig(ip_version=4, dst_ip="192.168.1.1", dst_port=8080)  # Wrong port
    ]
    
    # Basic IPv6 filtering test packets
    scenarios['ipv6_basic'] = [
        TestPackets.ipv6_http_packet("2001:db8::1"),      # Should match Rule 0
        TestPackets.ipv6_https_packet("2001:db8::2"),     # Should match Rule 1
        TestPackets.ipv6_http_packet("2001:db8::3"),      # Should not match
    ]
    
    # Mixed protocol packets
    scenarios['mixed_protocol'] = [
        TestPackets.ipv4_http_packet("192.168.1.1"),
        TestPackets.ipv6_https_packet("2001:db8::1"),
        TestPackets.ipv4_https_packet("192.168.1.2"),
        TestPackets.ipv6_http_packet("2001:db8::2"),
    ]
    
    # Edge case packets
    scenarios['edge_cases'] = [
        TestPackets.malformed_ethertype_packet(),
        TestPackets.truncated_packet(),
        TestPackets.jumbo_frame_packet(),
        PacketConfig(ip_version=4, dst_ip="192.168.1.1", payload_size=0),  # Minimum size
    ]
    
    # Performance test packets
    scenarios['performance'] = [
        PacketConfig(ip_version=4, dst_ip="192.168.1.1", dst_port=80, payload_size=size)
        for size in [64, 128, 256, 512, 1500]
    ]
    
    return scenarios


class ScapyPacketGenerator:
    """Scapy-based packet generator for creating AXI Stream test data."""
    
    def __init__(self, data_width: int = 512):
        """
        Initialize the Scapy packet generator.
        
        Args:
            data_width: AXI Stream data width in bits (default 512)
        """
        self.data_width = data_width
        self.data_bytes = data_width // 8
        self.packet_gen = PacketGenerator()
        
    def generate_ipv4_packet(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, 
                           payload_size: int = 0, protocol: str = "UDP") -> List[Tuple[int, int, bool, int]]:
        """
        Generate an IPv4 packet as AXI Stream beats.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address  
            src_port: Source port
            dst_port: Destination port
            payload_size: Payload size in bytes
            protocol: Protocol ("TCP" or "UDP")
            
        Returns:
            List of (tdata, tkeep, tlast, tuser) tuples
        """
        config = PacketConfig(
            ip_version=4,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            payload_size=payload_size
        )
        
        packet = self.packet_gen.generate_packet(config)
        return self._packet_to_axi_stream(packet)
        
    def generate_ipv6_packet(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                           payload_size: int = 0, protocol: str = "UDP") -> List[Tuple[int, int, bool, int]]:
        """
        Generate an IPv6 packet as AXI Stream beats.
        
        Args:
            src_ip: Source IPv6 address
            dst_ip: Destination IPv6 address
            src_port: Source port
            dst_port: Destination port
            payload_size: Payload size in bytes
            protocol: Protocol ("TCP" or "UDP")
            
        Returns:
            List of (tdata, tkeep, tlast, tuser) tuples
        """
        config = PacketConfig(
            ip_version=6,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            payload_size=payload_size
        )
        
        packet = self.packet_gen.generate_packet(config)
        return self._packet_to_axi_stream(packet)
        
    def generate_tcp_packet(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                          payload_size: int = 0, ip_version: int = 4) -> List[Tuple[int, int, bool, int]]:
        """Generate a TCP packet as AXI Stream beats."""
        config = PacketConfig(
            ip_version=ip_version,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol="TCP",
            payload_size=payload_size
        )
        
        packet = self.packet_gen.generate_packet(config)
        return self._packet_to_axi_stream(packet)
        
    def generate_udp_packet(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                          payload_size: int = 0, ip_version: int = 4) -> List[Tuple[int, int, bool, int]]:
        """Generate a UDP packet as AXI Stream beats."""
        config = PacketConfig(
            ip_version=ip_version,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol="UDP",
            payload_size=payload_size
        )
        
        packet = self.packet_gen.generate_packet(config)
        return self._packet_to_axi_stream(packet)
        
    def generate_malformed_packet(self, config: PacketConfig) -> List[Tuple[int, int, bool, int]]:
        """Generate a malformed packet for edge case testing."""
        packet = self.packet_gen.generate_packet(config)
        return self._packet_to_axi_stream(packet)
        
    def _packet_to_axi_stream(self, packet: bytes) -> List[Tuple[int, int, bool, int]]:
        """
        Convert a packet byte array to AXI Stream beats.
        
        Args:
            packet: Packet as bytes
            
        Returns:
            List of (tdata, tkeep, tlast, tuser) tuples
        """
        beats = []
        packet_len = len(packet)
        
        for i in range(0, packet_len, self.data_bytes):
            # Extract data for this beat
            beat_data = packet[i:i + self.data_bytes]
            bytes_in_beat = len(beat_data)
            
            # Pad to full width if needed
            if bytes_in_beat < self.data_bytes:
                beat_data += b'\x00' * (self.data_bytes - bytes_in_beat)
                
            # Convert to integer (little endian)
            tdata = int.from_bytes(beat_data, byteorder='little')
            
            # Create tkeep mask (1 bit per valid byte)
            tkeep = (1 << bytes_in_beat) - 1
            
            # Set tlast on final beat
            tlast = (i + self.data_bytes >= packet_len)
            
            # tuser can carry additional metadata (set to 0 for now)
            tuser = 0
            
            beats.append((tdata, tkeep, tlast, tuser))
            
        return beats
        
    def create_test_scenario(self, scenario_name: str) -> List[Tuple[PacketConfig, bool]]:
        """
        Create a test scenario with multiple packets.
        
        Args:
            scenario_name: Name of the scenario to create
            
        Returns:
            List of (packet_config, should_match) tuples
        """
        scenarios = create_test_scenario_packets()
        
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
            
        test_packets = []
        for config in scenarios[scenario_name]:
            # Determine if packet should match based on dst_ip and dst_port
            should_match = self._packet_should_match(config)
            test_packets.append((config, should_match))
            
        return test_packets
        
    def _packet_should_match(self, config: PacketConfig) -> bool:
        """
        Determine if a packet should match the default filter rules.
        
        Default rules:
        - Rule 0: IPv4 192.168.1.1:80 or IPv6 2001:db8::1:80
        - Rule 1: IPv4 192.168.1.2:443 or IPv6 2001:db8::2:443
        """
        if config.ip_version == 4:
            return ((config.dst_ip == "192.168.1.1" and config.dst_port == 80) or
                    (config.dst_ip == "192.168.1.2" and config.dst_port == 443))
        elif config.ip_version == 6:
            return ((config.dst_ip == "2001:db8::1" and config.dst_port == 80) or
                    (config.dst_ip == "2001:db8::2" and config.dst_port == 443))
        else:
            return False
