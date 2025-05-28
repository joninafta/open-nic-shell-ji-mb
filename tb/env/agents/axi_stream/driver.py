"""
AXI Stream driver for OpenNIC testbench environment.
Generates AXI Stream transactions.
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer
from typing import Any, Optional, Dict, List
import random

from ..base import Driver, Transaction


class AxiStreamTransaction(Transaction):
    """AXI Stream transaction class."""
    
    def __init__(self, data: List[int], keep: Optional[List[int]] = None, 
                 last: bool = False, user: int = 0, dest: int = 0, id_val: int = 0,
                 timestamp: float = 0.0):
        """
        Initialize AXI Stream transaction.
        
        Args:
            data: Data bytes
            keep: Keep signal for each byte (None for all valid)
            last: Last signal
            user: User signal value
            dest: Destination signal value
            id_val: ID signal value
            timestamp: Transaction timestamp
        """
        super().__init__(timestamp)
        self.data = data
        self.keep = keep if keep is not None else [1] * len(data)
        self.last = last
        self.user = user
        self.dest = dest
        self.id = id_val
        
    def __str__(self) -> str:
        return (f"AxiStreamTransaction(data={self.data}, keep={self.keep}, "
                f"last={self.last}, user={self.user}, dest={self.dest}, "
                f"id={self.id}, timestamp={self.timestamp})")


class AxiStreamDriver(Driver):
    """
    AXI Stream driver implementation.
    Drives AXI Stream interface with configurable timing.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject,
                 signals: Dict[str, cocotb.handle.HierarchyObject],
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize AXI Stream driver.
        
        Args:
            name: Driver instance name
            clock: Clock signal
            signals: Dictionary of AXI Stream signals
            config: Optional configuration
        """
        super().__init__(name, clock, config)
        
        # Required signals
        self.tvalid = signals['tvalid']
        self.tready = signals['tready']
        self.tdata = signals['tdata']
        
        # Optional signals
        self.tkeep = signals.get('tkeep')
        self.tlast = signals.get('tlast')
        self.tuser = signals.get('tuser')
        self.tdest = signals.get('tdest')
        self.tid = signals.get('tid')
        
        # Configuration
        self.data_width = len(self.tdata)
        self.backpressure_probability = config.get('backpressure_prob', 0.0) if config else 0.0
        self.min_gap_cycles = config.get('min_gap_cycles', 0) if config else 0
        self.max_gap_cycles = config.get('max_gap_cycles', 0) if config else 0
        
    async def send_transaction(self, transaction: AxiStreamTransaction) -> None:
        """
        Send a single AXI Stream transaction.
        
        Args:
            transaction: Transaction to send
        """
        if not self._active:
            return
            
        # Convert data to appropriate width
        data_bytes = len(transaction.data)
        bus_bytes = self.data_width // 8
        
        # Split transaction into bus-width chunks
        for offset in range(0, data_bytes, bus_bytes):
            chunk_data = transaction.data[offset:offset + bus_bytes]
            chunk_keep = transaction.keep[offset:offset + bus_bytes]
            is_last_chunk = (offset + bus_bytes >= data_bytes)
            
            # Pad chunk to bus width
            while len(chunk_data) < bus_bytes:
                chunk_data.append(0)
                chunk_keep.append(0)
                
            # Set up signals
            self.tvalid.value = 1
            
            # Pack data into single value
            data_value = 0
            for i, byte_val in enumerate(chunk_data):
                data_value |= (byte_val << (i * 8))
            self.tdata.value = data_value
            
            # Set optional signals
            if self.tkeep:
                keep_value = 0
                for i, keep_val in enumerate(chunk_keep):
                    keep_value |= (keep_val << i)
                self.tkeep.value = keep_value
                
            if self.tlast:
                self.tlast.value = 1 if (transaction.last and is_last_chunk) else 0
                
            if self.tuser:
                self.tuser.value = transaction.user
                
            if self.tdest:
                self.tdest.value = transaction.dest
                
            if self.tid:
                self.tid.value = transaction.id
                
            # Wait for ready
            await RisingEdge(self.clock)
            while self.tready.value != 1:
                await RisingEdge(self.clock)
                
        # Deassert valid
        self.tvalid.value = 0
        self._transactions_sent += 1
        
        # Optional gap between transactions
        if self.min_gap_cycles > 0 or self.max_gap_cycles > 0:
            gap_cycles = random.randint(self.min_gap_cycles, self.max_gap_cycles)
            await self.wait_clock_cycles(gap_cycles)
            
    async def send_random_transaction(self, min_size: int = 1, max_size: int = 64) -> AxiStreamTransaction:
        """
        Generate and send a random transaction.
        
        Args:
            min_size: Minimum packet size in bytes
            max_size: Maximum packet size in bytes
            
        Returns:
            The generated transaction
        """
        size = random.randint(min_size, max_size)
        data = [random.randint(0, 255) for _ in range(size)]
        
        transaction = AxiStreamTransaction(
            data=data,
            last=True,
            user=random.randint(0, 255),
            dest=random.randint(0, 15),
            id_val=random.randint(0, 15)
        )
        
        await self.send_transaction(transaction)
        return transaction
        
    async def send_burst(self, transactions: List[AxiStreamTransaction], 
                        inter_packet_delay: int = 0) -> None:
        """
        Send a burst of transactions.
        
        Args:
            transactions: List of transactions to send
            inter_packet_delay: Cycles between packets
        """
        for i, txn in enumerate(transactions):
            await self.send_transaction(txn)
            
            if i < len(transactions) - 1 and inter_packet_delay > 0:
                await self.wait_clock_cycles(inter_packet_delay)
                
    async def _reset_signals(self) -> None:
        """Reset AXI Stream signals to idle state."""
        self.tvalid.value = 0
        self.tdata.value = 0
        
        if self.tkeep:
            self.tkeep.value = 0
        if self.tlast:
            self.tlast.value = 0
        if self.tuser:
            self.tuser.value = 0
        if self.tdest:
            self.tdest.value = 0
        if self.tid:
            self.tid.value = 0
