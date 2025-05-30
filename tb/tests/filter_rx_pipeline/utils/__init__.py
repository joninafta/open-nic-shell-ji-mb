"""
Filter RX Pipeline Test Utilities

This package contains common utilities for testing the Filter RX Pipeline module.
"""

from .test_utils import (
    FilterRxTestbench,
    TestConfig,
    TestResult,
    CommonRules
)

from .packet_generator import (
    PacketGenerator,
    IPv4PacketTemplate,
    IPv6PacketTemplate,
    UDPPacketTemplate,
    TCPPacketTemplate
)

from .axi_stream_monitor import (
    AxiStreamMonitor,
    AxiStreamDriver,
    AxiStreamPacket
)

from .statistics_checker import (
    StatisticsChecker,
    PerformanceMetrics,
    verify_packet_statistics
)

__all__ = [
    # Test utilities
    'FilterRxTestbench',
    'TestResult',
    'CommonRules',
    
    # Packet generation
    'PacketGenerator',
    'IPv4PacketTemplate',
    'IPv6PacketTemplate', 
    'UDPPacketTemplate',
    'TCPPacketTemplate',
    
    # AXI Stream monitoring
    'AxiStreamMonitor',
    'AxiStreamDriver',
    'AxiStreamPacket',
    
    # Statistics verification
    'StatisticsChecker',
    'PerformanceMetrics',
    'verify_packet_statistics'
]
