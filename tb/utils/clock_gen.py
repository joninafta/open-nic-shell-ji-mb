"""
Clock generation utilities for OpenNIC testbench environment.
Provides flexible clock generation with configurable frequencies and phases.
"""

import cocotb
from cocotb.triggers import Timer
from typing import Optional, Dict, Any
import logging


class ClockGenerator:
    """
    Flexible clock generator for testbench environments.
    Supports multiple clocks with different frequencies and phases.
    """
    
    def __init__(self, name: str = "ClockGenerator"):
        """
        Initialize clock generator.
        
        Args:
            name: Generator instance name
        """
        self.name = name
        self.logger = logging.getLogger(f"cocotb.tb.{name}")
        self._running_clocks: Dict[str, cocotb.coroutine] = {}
        
    async def start_clock(self, signal: cocotb.handle.HierarchyObject, 
                         frequency_mhz: float, name: str = "clock",
                         duty_cycle: float = 50.0, phase_ns: float = 0.0) -> None:
        """
        Start a clock on the specified signal.
        
        Args:
            signal: Clock signal to drive
            frequency_mhz: Clock frequency in MHz
            name: Clock name for identification
            duty_cycle: Duty cycle percentage (0-100)
            phase_ns: Phase offset in nanoseconds
        """
        if name in self._running_clocks:
            self.logger.warning(f"Clock '{name}' already running, stopping first")
            await self.stop_clock(name)
            
        period_ns = 1000.0 / frequency_mhz
        high_time_ns = period_ns * (duty_cycle / 100.0)
        low_time_ns = period_ns - high_time_ns
        
        self.logger.info(f"Starting clock '{name}': {frequency_mhz} MHz, "
                        f"period={period_ns:.2f}ns, duty={duty_cycle}%, phase={phase_ns}ns")
        
        # Start clock coroutine
        clock_coro = cocotb.start_soon(self._clock_driver(
            signal, high_time_ns, low_time_ns, phase_ns, name
        ))
        self._running_clocks[name] = clock_coro
        
    async def _clock_driver(self, signal: cocotb.handle.HierarchyObject,
                           high_time_ns: float, low_time_ns: float,
                           phase_ns: float, name: str) -> None:
        """
        Internal clock driver coroutine.
        
        Args:
            signal: Signal to drive
            high_time_ns: High time in nanoseconds
            low_time_ns: Low time in nanoseconds
            phase_ns: Phase offset in nanoseconds
            name: Clock name for logging
        """
        try:
            # Initial phase delay
            if phase_ns > 0:
                await Timer(phase_ns, units='ns')
                
            # Initialize clock to 0
            signal.value = 0
            
            # Clock generation loop
            while True:
                # High phase
                signal.value = 1
                await Timer(high_time_ns, units='ns')
                
                # Low phase
                signal.value = 0
                await Timer(low_time_ns, units='ns')
                
        except Exception as e:
            self.logger.error(f"Clock '{name}' driver error: {e}")
            
    async def stop_clock(self, name: str) -> None:
        """
        Stop a running clock.
        
        Args:
            name: Name of clock to stop
        """
        if name in self._running_clocks:
            self._running_clocks[name].kill()
            del self._running_clocks[name]
            self.logger.info(f"Stopped clock '{name}'")
        else:
            self.logger.warning(f"Clock '{name}' not found")
            
    async def stop_all_clocks(self) -> None:
        """Stop all running clocks."""
        clock_names = list(self._running_clocks.keys())
        for name in clock_names:
            await self.stop_clock(name)
            
    def is_clock_running(self, name: str) -> bool:
        """
        Check if a clock is running.
        
        Args:
            name: Clock name to check
            
        Returns:
            True if clock is running
        """
        return name in self._running_clocks
        
    def get_running_clocks(self) -> list:
        """Get list of running clock names."""
        return list(self._running_clocks.keys())


class StandardClocks:
    """
    Predefined standard clocks for OpenNIC projects.
    """
    
    # Standard OpenNIC frequencies
    FREQ_250MHZ = 250.0
    FREQ_322MHZ = 322.265625  # Standard 322MHz for OpenNIC
    FREQ_100MHZ = 100.0
    FREQ_156MHZ = 156.25     # Common for 10G Ethernet
    
    @classmethod
    async def start_opennic_clocks(cls, generator: ClockGenerator,
                                  clock_signals: Dict[str, cocotb.handle.HierarchyObject],
                                  box_freq: str = "250mhz") -> None:
        """
        Start standard OpenNIC clocks.
        
        Args:
            generator: Clock generator instance
            clock_signals: Dictionary mapping clock names to signals
            box_freq: Box frequency ("250mhz" or "322mhz")
        """
        base_freq = cls.FREQ_250MHZ if box_freq == "250mhz" else cls.FREQ_322MHZ
        
        # Standard clock configurations
        clock_configs = {
            'clk': base_freq,
            'clk_100mhz': cls.FREQ_100MHZ,
            'clk_156mhz': cls.FREQ_156MHZ,
        }
        
        # Start configured clocks
        for clock_name, frequency in clock_configs.items():
            if clock_name in clock_signals:
                await generator.start_clock(
                    signal=clock_signals[clock_name],
                    frequency_mhz=frequency,
                    name=clock_name
                )


async def create_standard_testbench_clocks(dut: cocotb.handle.HierarchyObject,
                                         box_freq: str = "250mhz") -> ClockGenerator:
    """
    Create and start standard testbench clocks.
    
    Args:
        dut: Device under test handle
        box_freq: Box frequency specification
        
    Returns:
        Configured clock generator
    """
    generator = ClockGenerator("TestbenchClocks")
    
    # Map DUT signals to clock names
    clock_signals = {}
    
    # Common clock signal names
    clock_names = ['clk', 'clock', 'clk_250mhz', 'clk_322mhz', 'clk_100mhz', 'clk_156mhz']
    
    for name in clock_names:
        if hasattr(dut, name):
            clock_signals[name] = getattr(dut, name)
            
    # Start standard clocks
    await StandardClocks.start_opennic_clocks(generator, clock_signals, box_freq)
    
    return generator


class ClockDomainCrossing:
    """
    Utilities for handling clock domain crossing in testbenches.
    """
    
    @staticmethod
    async def sync_to_clock(clock: cocotb.handle.HierarchyObject, cycles: int = 1) -> None:
        """
        Synchronize to a clock domain.
        
        Args:
            clock: Clock signal to sync to
            cycles: Number of cycles to wait
        """
        from cocotb.triggers import RisingEdge
        
        for _ in range(cycles):
            await RisingEdge(clock)
            
    @staticmethod
    async def cross_clock_domains(source_clock: cocotb.handle.HierarchyObject,
                                 dest_clock: cocotb.handle.HierarchyObject,
                                 sync_cycles: int = 2) -> None:
        """
        Safely cross from one clock domain to another.
        
        Args:
            source_clock: Source clock domain
            dest_clock: Destination clock domain  
            sync_cycles: Synchronizer depth
        """
        from cocotb.triggers import RisingEdge
        
        # Wait for source clock edge
        await RisingEdge(source_clock)
        
        # Synchronize to destination domain
        for _ in range(sync_cycles):
            await RisingEdge(dest_clock)
