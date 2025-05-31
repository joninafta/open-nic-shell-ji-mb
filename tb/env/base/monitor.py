"""
Abstract monitor base class for OpenNIC testbench environment.
Provides common monitor functionality and interface.
"""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Edge
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Callable, List
import logging

from .component import Component


class Transaction:
    """Base transaction class for monitor observations."""
    
    def __init__(self, timestamp: float = 0.0):
        self.timestamp = timestamp
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(timestamp={self.timestamp})"


class Monitor(Component):
    """
    Abstract base class for all monitors in the testbench.
    Monitors observe interface activity and collect transactions.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject, config: Optional[Dict[str, Any]] = None):
        """
        Initialize monitor.
        
        Args:
            name: Monitor instance name
            clock: Clock signal for synchronization
            config: Optional configuration dictionary
        """
        super().__init__(name, config)
        self.clock = clock
        self._active = False
        self._transactions_observed = 0
        self._observers: List[Callable[[Transaction], None]] = []
        
    @property
    def transactions_observed(self) -> int:
        """Get number of transactions observed by this monitor."""
        return self._transactions_observed
        
    def add_observer(self, callback: Callable[[Transaction], None]) -> None:
        """
        Add observer callback for transactions.
        
        Args:
            callback: Function to call when transaction is observed
        """
        self._observers.append(callback)
        
    def remove_observer(self, callback: Callable[[Transaction], None]) -> None:
        """
        Remove observer callback.
        
        Args:
            callback: Function to remove from observers
        """
        if callback in self._observers:
            self._observers.remove(callback)
            
    def notify_observers(self, transaction: Transaction) -> None:
        """
        Notify all observers of a new transaction.
        
        Args:
            transaction: Transaction to broadcast
        """
        self._transactions_observed += 1
        for observer in self._observers:
            try:
                observer(transaction)
            except Exception as e:
                self.logger.error(f"Observer callback failed: {e}")
                
    @abstractmethod
    async def _monitor_interface(self) -> None:
        """Implementation-specific interface monitoring."""
        pass
        
    async def start(self) -> None:
        """Start the monitor."""
        await super().start()
        self._active = True
        # Start monitoring in background
        cocotb.start_soon(self._monitor_loop())
        
    async def stop(self) -> None:
        """Stop the monitor."""
        self._active = False
        await super().stop()
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.debug(f"Starting {self.name} monitoring loop")
        try:
            while self._active:
                await self._monitor_interface()
        except Exception as e:
            self.logger.error(f"Monitor loop error: {e}")
            raise
        finally:
            self.logger.debug(f"Stopped {self.name} monitoring loop")
            
    async def wait_for_transaction(self, timeout_cycles: Optional[int] = None) -> Transaction:
        """
        Wait for next transaction with optional timeout.
        
        Args:
            timeout_cycles: Maximum cycles to wait (None for no timeout)
            
        Returns:
            Next observed transaction
            
        Raises:
            TimeoutError: If timeout expires before transaction
        """
        start_count = self._transactions_observed
        cycles_waited = 0
        
        while self._transactions_observed == start_count:
            await RisingEdge(self.clock)
            cycles_waited += 1
            
            if timeout_cycles and cycles_waited >= timeout_cycles:
                raise TimeoutError(f"Timeout waiting for transaction on {self.name}")
                
        # Return the most recent transaction (implementation specific)
        return await self._get_last_transaction()
        
    @abstractmethod
    async def _get_last_transaction(self) -> Transaction:
        """Get the most recently observed transaction."""
        pass
