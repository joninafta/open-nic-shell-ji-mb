"""
Main testbench environment for OpenNIC filter_rx_pipeline testing.
Composes all agents, monitors, and components into a complete verification environment.
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from typing import Any, Optional, Dict, List
import logging

from .base import Component, Config, Scoreboard, Coverage
from .agents.axi_stream import AxiStreamDriver, AxiStreamMonitor
from .agents.filter_rx import FilterRxDriver, FilterRxMonitor


class FilterRxPipelineEnvironment(Component):
    """
    Complete verification environment for filter_rx_pipeline module.
    Manages all agents, scoreboards, and coverage collection.
    """
    
    def __init__(self, dut: cocotb.handle.HierarchyObject, config: Config):
        """
        Initialize the verification environment.
        
        Args:
            dut: Handle to the device under test
            config: Test configuration
        """
        super().__init__("FilterRxPipelineEnv", config.__dict__)
        
        self.dut = dut
        self.config = config
        
        # Get clock from DUT
        self.clock = dut.clk
        
        # Initialize components
        self._init_agents()
        self._init_scoreboards() 
        self._init_coverage()
        
        # Test control
        self._test_running = False
        
    def _init_agents(self) -> None:
        """Initialize all agents and monitors."""
        # Input AXI Stream driver
        input_signals = {
            'tvalid': self.dut.s_axis_rx_tvalid,
            'tready': self.dut.s_axis_rx_tready,
            'tdata': self.dut.s_axis_rx_tdata,
            'tkeep': self.dut.s_axis_rx_tkeep,
            'tlast': self.dut.s_axis_rx_tlast,
            'tuser': self.dut.s_axis_rx_tuser
        }
        
        self.input_driver = AxiStreamDriver(
            name="input_driver",
            clock=self.clock,
            signals=input_signals,
            config=self.config.test_config.driver_config
        )
        
        # Output AXI Stream monitor
        output_signals = {
            'tvalid': self.dut.m_axis_rx_tvalid,
            'tready': self.dut.m_axis_rx_tready,
            'tdata': self.dut.m_axis_rx_tdata,
            'tkeep': self.dut.m_axis_rx_tkeep,
            'tlast': self.dut.m_axis_rx_tlast,
            'tuser': self.dut.m_axis_rx_tuser
        }
        
        self.output_monitor = AxiStreamMonitor(
            name="output_monitor",
            clock=self.clock,
            signals=output_signals,
            config=self.config.test_config.monitor_config
        )
        
        # Filter-specific driver and monitor
        filter_status_signals = {}
        if hasattr(self.dut, 'filter_drop_valid'):
            filter_status_signals['drop_valid'] = self.dut.filter_drop_valid
        if hasattr(self.dut, 'filter_drop_reason'):
            filter_status_signals['drop_reason'] = self.dut.filter_drop_reason
            
        self.filter_driver = FilterRxDriver(
            name="filter_driver",
            clock=self.clock,
            axi_stream_driver=self.input_driver,
            config_signals={},  # Would map to actual config interface
            config=self.config.filter_config.__dict__
        )
        
        self.filter_monitor = FilterRxMonitor(
            name="filter_monitor", 
            clock=self.clock,
            output_monitor=self.output_monitor,
            filter_status_signals=filter_status_signals,
            config=self.config.test_config.monitor_config
        )
        
        # Configure output monitor ready signal
        if hasattr(self.dut, 'm_axis_rx_tready'):
            self.dut.m_axis_rx_tready.value = 1  # Always ready for now
            
    def _init_scoreboards(self) -> None:
        """Initialize scoreboards for checking."""
        self.packet_scoreboard = Scoreboard(
            name="packet_scoreboard",
            config=self.config.test_config.scoreboard_config
        )
        
        # Set up packet comparison function
        def compare_packets(expected, actual):
            """Compare expected vs actual packets."""
            if hasattr(expected, 'data') and hasattr(actual, 'data'):
                return expected.data == actual.data
            return str(expected) == str(actual)
            
        self.packet_scoreboard.set_comparison_function(compare_packets)
        
    def _init_coverage(self) -> None:
        """Initialize functional coverage collection."""
        self.coverage = Coverage(
            name="filter_coverage",
            config=self.config.test_config.coverage_config
        )
        
        # Create coverage groups
        self._setup_filter_coverage()
        self._setup_packet_coverage()
        
    def _setup_filter_coverage(self) -> None:
        """Set up filter-specific coverage points."""
        from .base import CoverageType
        
        # Filter rule coverage
        self.coverage.create_group("filter_rules", "Coverage of filter rule usage")
        
        # Add coverage points for each configured rule
        for i, rule in enumerate(self.config.filter_config.rules):
            self.coverage.add_coverage_point(
                "filter_rules", f"rule_{i}",
                CoverageType.FEATURE,
                f"Rule {i} hit coverage",
                target_hits=10
            )
            
        # Packet type coverage
        self.coverage.create_group("packet_types", "Coverage of different packet types")
        self.coverage.add_coverage_point(
            "packet_types", "matching_packets",
            CoverageType.FEATURE,
            "Packets that match filter rules",
            target_hits=50
        )
        self.coverage.add_coverage_point(
            "packet_types", "non_matching_packets", 
            CoverageType.FEATURE,
            "Packets that don't match any rules",
            target_hits=20
        )
        
    def _setup_packet_coverage(self) -> None:
        """Set up packet size and type coverage."""
        from .base import CoverageType
        
        # Packet size coverage  
        self.coverage.create_group("packet_sizes", "Coverage of packet sizes")
        size_bins = ["small_64", "medium_256", "large_1024", "jumbo_1500"]
        self.coverage.add_coverage_point(
            "packet_sizes", "size_distribution",
            CoverageType.FEATURE,
            "Distribution of packet sizes",
            bins=size_bins
        )
        
    async def configure_filter_rules(self) -> None:
        """Configure all filter rules from config."""
        for i, rule in enumerate(self.config.filter_config.rules):
            rule_dict = {
                'src_mac': rule.src_mac,
                'dst_mac': rule.dst_mac,
                'eth_type': rule.eth_type,
                'src_ip': rule.src_ip,
                'dst_ip': rule.dst_ip,
                'src_port': rule.src_port,
                'dst_port': rule.dst_port,
                'protocol': rule.protocol
            }
            
            # Remove None values
            rule_dict = {k: v for k, v in rule_dict.items() if v is not None}
            
            await self.filter_driver.configure_filter_rule(i, rule_dict)
            
    async def reset_dut(self) -> None:
        """Reset the device under test."""
        self.logger.info("Resetting DUT")
        
        # Assert reset
        if hasattr(self.dut, 'rst_n'):
            self.dut.rst_n.value = 0
        elif hasattr(self.dut, 'rst'):
            self.dut.rst.value = 1
        elif hasattr(self.dut, 'aresetn'):
            self.dut.aresetn.value = 0
            
        # Wait several clock cycles
        for _ in range(10):
            await RisingEdge(self.clock)
            
        # Deassert reset
        if hasattr(self.dut, 'rst_n'):
            self.dut.rst_n.value = 1
        elif hasattr(self.dut, 'rst'):
            self.dut.rst.value = 0
        elif hasattr(self.dut, 'aresetn'):
            self.dut.aresetn.value = 1
            
        # Wait for reset to settle
        for _ in range(10):
            await RisingEdge(self.clock)
            
        self.logger.info("DUT reset complete")
        
    async def run_basic_test(self) -> None:
        """Run a basic functional test."""
        self.logger.info("Starting basic filter test")
        
        # Configure filter rules
        await self.configure_filter_rules()
        
        # Generate and send test packets
        matching_packets, non_matching_packets = await self.filter_driver.send_test_sequence(
            num_matching=5, num_non_matching=3
        )
        
        # Wait for packets to be processed
        total_expected_output = len(matching_packets)  # Only matching packets should pass
        success = await self.filter_monitor.wait_for_packets(total_expected_output, timeout_cycles=1000)
        
        if not success:
            self.test_failed("Did not receive expected number of output packets")
            
        # Check statistics
        stats = self.filter_monitor.get_filter_statistics()
        self.logger.info(f"Test completed: {stats['packets_passed']} passed, {stats['packets_dropped']} dropped")
        
        # Update coverage
        self.coverage.hit_coverage_point("packet_types", "matching_packets")
        self.coverage.hit_coverage_point("packet_types", "non_matching_packets")
        
    async def run_stress_test(self, num_packets: int = 100) -> None:
        """Run a stress test with many packets."""
        self.logger.info(f"Starting stress test with {num_packets} packets")
        
        # Configure filter rules
        await self.configure_filter_rules()
        
        # Send many packets quickly
        for i in range(num_packets):
            if i % 2 == 0:
                # Send matching packet
                rule_index = i % len(self.config.filter_config.rules)
                packet = self.filter_driver.generate_matching_packet(rule_index)
                await self.filter_driver.send_filter_packet(packet)
                self.coverage.hit_coverage_point("filter_rules", f"rule_{rule_index}")
            else:
                # Send non-matching packet
                packet = self.filter_driver.generate_non_matching_packet()
                await self.filter_driver.send_filter_packet(packet)
                
        # Wait for all packets to be processed
        expected_output = num_packets // 2  # Roughly half should match
        await Timer(1000, units='ns')  # Give time for processing
        
        stats = self.filter_monitor.get_filter_statistics()
        self.logger.info(f"Stress test completed: {stats['packets_passed']} passed, {stats['packets_dropped']} dropped")
        
    async def start(self) -> None:
        """Start the verification environment."""
        await super().start()
        self._test_running = True
        
        # Start all components
        await self.input_driver.start()
        await self.output_monitor.start()
        await self.filter_driver.start()
        await self.filter_monitor.start()
        await self.packet_scoreboard.start()
        await self.coverage.start()
        
        self.logger.info("Verification environment started")
        
    async def stop(self) -> None:
        """Stop the verification environment."""
        self._test_running = False
        
        # Stop all components
        await self.input_driver.stop()
        await self.output_monitor.stop()
        await self.filter_driver.stop()
        await self.filter_monitor.stop()
        await self.packet_scoreboard.stop()
        await self.coverage.stop()
        
        # Report final statistics
        self.filter_monitor.report_statistics()
        
        await super().stop()
        self.logger.info("Verification environment stopped")
        
    def get_environment_status(self) -> Dict[str, Any]:
        """Get overall environment status."""
        return {
            'test_running': self._test_running,
            'input_transactions': self.input_driver.transactions_sent,
            'output_transactions': self.output_monitor.transactions_observed,
            'filter_stats': self.filter_monitor.get_filter_statistics(),
            'scoreboard_stats': self.packet_scoreboard.stats,
            'coverage_percent': self.coverage.get_coverage_percent()
        }
