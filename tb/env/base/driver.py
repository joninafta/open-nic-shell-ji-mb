"""
Abstract driver base class for OpenNIC testbench environment.
Provides common driver functionality and interface.
"""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import logging

from .component import Component


class Driver(Component):
    """
    Abstract base class for all drivers in the testbench.
    Drivers are responsible for generating stimulus on DUT interfaces.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject, config: Optional[Dict[str, Any]] = None):
        """
        Initialize driver.
        
        Args:
            name: Driver instance name
            clock: Clock signal for synchronization
            config: Optional configuration dictionary
        """
        super().__init__(name, config)
        self.clock = clock
        self._active = False
        self._transactions_sent = 0
        
    @property
    def transactions_sent(self) -> int:
        """Get number of transactions sent by this driver."""
        return self._transactions_sent
        
    @abstractmethod
    async def send_transaction(self, transaction: Any) -> None:
        """
        Send a single transaction on the interface.
        
        Args:
            transaction: Transaction object to send
        """
        pass
        
    async def send_transactions(self, transactions: List[Any], spacing: int = 1) -> None:
        """
        Send multiple transactions with optional spacing.
        
        Args:
            transactions: List of transaction objects
            spacing: Clock cycles between transactions
        """
        for txn in transactions:
            await self.send_transaction(txn)
            if spacing > 0:
                for _ in range(spacing):
                    await RisingEdge(self.clock)
                    
    async def wait_clock_cycles(self, cycles: int) -> None:
        """Wait for specified number of clock cycles."""
        for _ in range(cycles):
            await RisingEdge(self.clock)
            
    async def reset_interface(self) -> None:
        """Reset interface signals to idle state."""
        self.logger.debug(f"Resetting {self.name} interface")
        await self._reset_signals()
        
    @abstractmethod
    async def _reset_signals(self) -> None:
        """Implementation-specific signal reset."""
        pass
        
    async def start(self) -> None:
        """Start the driver."""
        await super().start()
        self._active = True
        await self.reset_interface()
        
    async def stop(self) -> None:
        """Stop the driver."""
        self._active = False
        await super().stop()
