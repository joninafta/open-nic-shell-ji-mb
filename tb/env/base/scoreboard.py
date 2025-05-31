"""
Scoreboard base class for OpenNIC testbench environment.
Provides transaction checking and comparison functionality.
"""

import cocotb
from typing import Any, Optional, Dict, List, Callable
import logging
from collections import deque
from dataclasses import dataclass

from .component import Component
from .monitor import Transaction


@dataclass
class ScoreboardStats:
    """Statistics for scoreboard operation."""
    transactions_checked: int = 0
    matches: int = 0
    mismatches: int = 0
    expected_pending: int = 0
    actual_pending: int = 0


class Scoreboard(Component):
    """
    Base scoreboard class for checking DUT behavior.
    Compares expected vs actual transactions.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scoreboard.
        
        Args:
            name: Scoreboard instance name
            config: Optional configuration dictionary
        """
        super().__init__(name, config)
        self._expected_queue: deque = deque()
        self._actual_queue: deque = deque()
        self._stats = ScoreboardStats()
        self._comparison_func: Optional[Callable[[Transaction, Transaction], bool]] = None
        self._mismatch_handlers: List[Callable[[Transaction, Transaction], None]] = []
        
    @property
    def stats(self) -> ScoreboardStats:
        """Get scoreboard statistics."""
        self._stats.expected_pending = len(self._expected_queue)
        self._stats.actual_pending = len(self._actual_queue)
        return self._stats
        
    def set_comparison_function(self, func: Callable[[Transaction, Transaction], bool]) -> None:
        """
        Set custom comparison function for transactions.
        
        Args:
            func: Function that returns True if transactions match
        """
        self._comparison_func = func
        
    def add_mismatch_handler(self, handler: Callable[[Transaction, Transaction], None]) -> None:
        """
        Add handler for transaction mismatches.
        
        Args:
            handler: Function called on mismatch (expected, actual)
        """
        self._mismatch_handlers.append(handler)
        
    def add_expected_transaction(self, transaction: Transaction) -> None:
        """
        Add expected transaction to queue.
        
        Args:
            transaction: Expected transaction
        """
        self._expected_queue.append(transaction)
        self.logger.debug(f"Added expected transaction: {transaction}")
        self._try_check_transactions()
        
    def add_actual_transaction(self, transaction: Transaction) -> None:
        """
        Add actual transaction from DUT.
        
        Args:
            transaction: Actual transaction observed
        """
        self._actual_queue.append(transaction)
        self.logger.debug(f"Added actual transaction: {transaction}")
        self._try_check_transactions()
        
    def _try_check_transactions(self) -> None:
        """Check transactions if both queues have items."""
        while self._expected_queue and self._actual_queue:
            expected = self._expected_queue.popleft()
            actual = self._actual_queue.popleft()
            
            self._stats.transactions_checked += 1
            
            if self._compare_transactions(expected, actual):
                self._stats.matches += 1
                self.logger.debug(f"Transaction match: {expected}")
            else:
                self._stats.mismatches += 1
                self.logger.error(f"Transaction mismatch!")
                self.logger.error(f"  Expected: {expected}")
                self.logger.error(f"  Actual:   {actual}")
                
                # Call mismatch handlers
                for handler in self._mismatch_handlers:
                    try:
                        handler(expected, actual)
                    except Exception as e:
                        self.logger.error(f"Mismatch handler error: {e}")
                        
                # Fail test on mismatch
                self.test_failed(f"Transaction mismatch in {self.name}")
                
    def _compare_transactions(self, expected: Transaction, actual: Transaction) -> bool:
        """
        Compare two transactions.
        
        Args:
            expected: Expected transaction
            actual: Actual transaction
            
        Returns:
            True if transactions match
        """
        if self._comparison_func:
            return self._comparison_func(expected, actual)
        else:
            # Default comparison (can be overridden)
            return self._default_compare(expected, actual)
            
    def _default_compare(self, expected: Transaction, actual: Transaction) -> bool:
        """
        Default transaction comparison.
        Override in subclasses for specific comparison logic.
        
        Args:
            expected: Expected transaction
            actual: Actual transaction
            
        Returns:
            True if transactions match
        """
        # Basic comparison - override in subclasses
        return str(expected) == str(actual)
        
    def check_empty(self) -> bool:
        """
        Check if both queues are empty.
        
        Returns:
            True if no pending transactions
        """
        return len(self._expected_queue) == 0 and len(self._actual_queue) == 0
        
    def flush_queues(self) -> None:
        """Clear all pending transactions."""
        expected_count = len(self._expected_queue)
        actual_count = len(self._actual_queue)
        
        self._expected_queue.clear()
        self._actual_queue.clear()
        
        if expected_count > 0 or actual_count > 0:
            self.logger.warning(f"Flushed {expected_count} expected, {actual_count} actual transactions")
            
    def report_status(self) -> None:
        """Log current scoreboard status."""
        stats = self.stats
        self.logger.info(f"Scoreboard {self.name} Status:")
        self.logger.info(f"  Transactions checked: {stats.transactions_checked}")
        self.logger.info(f"  Matches: {stats.matches}")
        self.logger.info(f"  Mismatches: {stats.mismatches}")
        self.logger.info(f"  Expected pending: {stats.expected_pending}")
        self.logger.info(f"  Actual pending: {stats.actual_pending}")
        
    async def wait_for_completion(self, timeout_ms: float = 1000.0) -> None:
        """
        Wait for all transactions to be processed.
        
        Args:
            timeout_ms: Timeout in milliseconds
        """
        import cocotb
        from cocotb.triggers import Timer
        
        start_time = cocotb.utils.get_sim_time('ms')
        
        while not self.check_empty():
            await Timer(1, units='ms')
            current_time = cocotb.utils.get_sim_time('ms')
            
            if current_time - start_time > timeout_ms:
                self.logger.error(f"Timeout waiting for scoreboard completion")
                self.report_status()
                raise TimeoutError(f"Scoreboard {self.name} completion timeout")
                
        self.logger.info(f"Scoreboard {self.name} completed successfully")
        
    async def start(self) -> None:
        """Start the scoreboard."""
        await super().start()
        self.logger.debug(f"Scoreboard {self.name} started")
        
    async def stop(self) -> None:
        """Stop the scoreboard and report final status."""
        self.report_status()
        if not self.check_empty():
            self.logger.warning(f"Scoreboard {self.name} stopped with pending transactions")
        await super().stop()
