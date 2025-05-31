"""
Reset utilities for OpenNIC testbench environment.
Provides standardized reset sequence handling.
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from typing import Optional, List, Dict, Any
import logging


class ResetManager:
    """
    Manages reset sequences for OpenNIC testbenches.
    Handles different reset polarities and sequencing.
    """
    
    def __init__(self, name: str = "ResetManager"):
        """
        Initialize reset manager.
        
        Args:
            name: Manager instance name
        """
        self.name = name
        self.logger = logging.getLogger(f"cocotb.tb.{name}")
        
    async def reset_dut(self, dut: cocotb.handle.HierarchyObject,
                       clock: cocotb.handle.HierarchyObject,
                       reset_cycles: int = 10,
                       settle_cycles: int = 10) -> None:
        """
        Perform a standard DUT reset sequence.
        
        Args:
            dut: Device under test handle
            clock: Clock signal for synchronization
            reset_cycles: Number of cycles to hold reset
            settle_cycles: Number of cycles after reset release
        """
        self.logger.info(f"Starting reset sequence: {reset_cycles} reset cycles, {settle_cycles} settle cycles")
        
        # Detect reset signal type and polarity
        reset_signal, active_value, inactive_value = self._detect_reset_signal(dut)
        
        if reset_signal is None:
            self.logger.warning("No reset signal detected, skipping reset")
            return
            
        self.logger.debug(f"Using reset signal: {reset_signal._name}, active={active_value}")
        
        # Assert reset
        reset_signal.value = active_value
        
        # Hold reset for specified cycles
        for cycle in range(reset_cycles):
            await RisingEdge(clock)
            if cycle % 5 == 0:
                self.logger.debug(f"Reset cycle {cycle}/{reset_cycles}")
                
        # Release reset
        reset_signal.value = inactive_value
        self.logger.debug("Reset released")
        
        # Wait for design to settle
        for cycle in range(settle_cycles):
            await RisingEdge(clock)
            if cycle % 5 == 0:
                self.logger.debug(f"Settle cycle {cycle}/{settle_cycles}")
                
        self.logger.info("Reset sequence complete")
        
    def _detect_reset_signal(self, dut: cocotb.handle.HierarchyObject) -> tuple:
        """
        Detect reset signal and determine polarity.
        
        Args:
            dut: Device under test handle
            
        Returns:
            Tuple of (signal, active_value, inactive_value)
        """
        # Common reset signal names and their polarities
        reset_candidates = [
            ('rst_n', 0, 1),      # Active low
            ('resetn', 0, 1),     # Active low
            ('aresetn', 0, 1),    # AXI reset, active low
            ('rst', 1, 0),        # Active high
            ('reset', 1, 0),      # Active high
            ('areset', 1, 0),     # Active high
        ]
        
        for signal_name, active_val, inactive_val in reset_candidates:
            if hasattr(dut, signal_name):
                signal = getattr(dut, signal_name)
                self.logger.debug(f"Found reset signal: {signal_name}")
                return signal, active_val, inactive_val
                
        return None, None, None
        
    async def reset_multiple_domains(self, reset_domains: List[Dict[str, Any]],
                                   global_settle_cycles: int = 10) -> None:
        """
        Reset multiple clock domains in sequence.
        
        Args:
            reset_domains: List of domain configurations
            global_settle_cycles: Cycles to wait after all resets
        """
        self.logger.info(f"Resetting {len(reset_domains)} clock domains")
        
        for i, domain in enumerate(reset_domains):
            domain_name = domain.get('name', f'domain_{i}')
            self.logger.info(f"Resetting domain: {domain_name}")
            
            await self.reset_dut(
                dut=domain['dut'],
                clock=domain['clock'],
                reset_cycles=domain.get('reset_cycles', 10),
                settle_cycles=domain.get('settle_cycles', 5)
            )
            
        # Global settle time
        if global_settle_cycles > 0:
            self.logger.info(f"Global settle: {global_settle_cycles} cycles")
            # Use first domain's clock for global settling
            if reset_domains:
                first_clock = reset_domains[0]['clock']
                for _ in range(global_settle_cycles):
                    await RisingEdge(first_clock)
                    
    async def controlled_reset_release(self, dut: cocotb.handle.HierarchyObject,
                                     clock: cocotb.handle.HierarchyObject,
                                     reset_cycles: int = 10,
                                     release_delay_ns: float = 0.0) -> None:
        """
        Reset with controlled timing for reset release.
        
        Args:
            dut: Device under test handle
            clock: Clock signal
            reset_cycles: Cycles to hold reset
            release_delay_ns: Delay before reset release (for timing tests)
        """
        reset_signal, active_value, inactive_value = self._detect_reset_signal(dut)
        
        if reset_signal is None:
            self.logger.warning("No reset signal detected")
            return
            
        # Assert reset
        reset_signal.value = active_value
        
        # Hold reset
        for _ in range(reset_cycles):
            await RisingEdge(clock)
            
        # Optional delay before release
        if release_delay_ns > 0:
            await Timer(release_delay_ns, units='ns')
            
        # Release reset
        reset_signal.value = inactive_value
        
        # Wait one more cycle
        await RisingEdge(clock)


class PowerOnReset:
    """
    Simulates power-on reset sequences.
    """
    
    @staticmethod
    async def power_on_sequence(dut: cocotb.handle.HierarchyObject,
                               clock: cocotb.handle.HierarchyObject,
                               power_on_delay_ns: float = 1000.0,
                               reset_cycles: int = 20) -> None:
        """
        Simulate power-on reset sequence.
        
        Args:
            dut: Device under test
            clock: Clock signal
            power_on_delay_ns: Delay to simulate power stabilization
            reset_cycles: Reset duration in cycles
        """
        logger = logging.getLogger("cocotb.tb.PowerOnReset")
        
        logger.info(f"Starting power-on sequence: {power_on_delay_ns}ns power delay")
        
        # Simulate power-on delay
        await Timer(power_on_delay_ns, units='ns')
        
        # Perform reset
        reset_mgr = ResetManager("PowerOnReset")
        await reset_mgr.reset_dut(dut, clock, reset_cycles)
        
        logger.info("Power-on sequence complete")


class ResetSynchronizer:
    """
    Utilities for reset synchronization across clock domains.
    """
    
    @staticmethod
    async def sync_reset_release(reset_signal: cocotb.handle.HierarchyObject,
                                clock: cocotb.handle.HierarchyObject,
                                sync_stages: int = 2) -> None:
        """
        Synchronously release reset.
        
        Args:
            reset_signal: Reset signal to control
            clock: Clock for synchronization
            sync_stages: Number of synchronizer stages
        """
        logger = logging.getLogger("cocotb.tb.ResetSync")
        
        # Assume active low reset
        reset_signal.value = 0  # Assert reset
        
        # Wait for clock edges to ensure proper synchronization
        for stage in range(sync_stages):
            await RisingEdge(clock)
            logger.debug(f"Reset sync stage {stage + 1}/{sync_stages}")
            
        # Release reset synchronously
        await RisingEdge(clock)
        reset_signal.value = 1  # Release reset
        
        # Wait one more cycle for good measure
        await RisingEdge(clock)
        
        logger.info("Synchronous reset release complete")


# Convenience functions for common reset scenarios

async def opennic_standard_reset(dut: cocotb.handle.HierarchyObject,
                                clock: cocotb.handle.HierarchyObject) -> None:
    """
    Standard reset sequence for OpenNIC designs.
    
    Args:
        dut: Device under test
        clock: Primary clock
    """
    reset_mgr = ResetManager("OpenNICReset")
    await reset_mgr.reset_dut(
        dut=dut,
        clock=clock,
        reset_cycles=20,    # Longer reset for complex designs
        settle_cycles=15    # Allow time for internal state machines
    )


async def quick_reset(dut: cocotb.handle.HierarchyObject,
                     clock: cocotb.handle.HierarchyObject) -> None:
    """
    Quick reset for simple tests.
    
    Args:
        dut: Device under test
        clock: Clock signal
    """
    reset_mgr = ResetManager("QuickReset")
    await reset_mgr.reset_dut(
        dut=dut,
        clock=clock,
        reset_cycles=5,
        settle_cycles=3
    )


async def reset_with_power_on(dut: cocotb.handle.HierarchyObject,
                             clock: cocotb.handle.HierarchyObject,
                             power_delay_ns: float = 1000.0) -> None:
    """
    Reset with power-on simulation.
    
    Args:
        dut: Device under test
        clock: Clock signal
        power_delay_ns: Power stabilization delay
    """
    await PowerOnReset.power_on_sequence(
        dut=dut,
        clock=clock,
        power_on_delay_ns=power_delay_ns,
        reset_cycles=25
    )
