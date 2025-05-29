"""
AXI Stream monitor for OpenNIC testbench environment.
Observes AXI Stream transactions.
"""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from typing import Any, Optional, Dict, List

from ...base import Monitor, Transaction
from .driver import AxiStreamTransaction


class AxiStreamMonitor(Monitor):
    """
    AXI Stream monitor implementation.
    Observes and captures AXI Stream transactions.
    """
    
    def __init__(self, name: str, clock: cocotb.handle.HierarchyObject,
                 signals: Dict[str, cocotb.handle.HierarchyObject],
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize AXI Stream monitor.
        
        Args:
            name: Monitor instance name
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
        self.bus_bytes = self.data_width // 8
        
        # Current transaction being assembled
        self._current_transaction: Optional[List[int]] = None
        self._current_keep: Optional[List[int]] = None
        self._current_user: int = 0
        self._current_dest: int = 0
        self._current_id: int = 0
        self._last_transaction: Optional[AxiStreamTransaction] = None
        
    async def _monitor_interface(self) -> None:
        """Monitor AXI Stream interface for transactions."""
        await RisingEdge(self.clock)
        await ReadOnly()
        
        # Check for valid transaction
        if self.tvalid.value == 1 and self.tready.value == 1:
            await self._capture_beat()
            
    async def _capture_beat(self) -> None:
        """Capture a single AXI Stream beat."""
        # Get data value
        data_value = int(self.tdata.value)
        
        # Extract bytes from data
        beat_data = []
        beat_keep = []
        
        for i in range(self.bus_bytes):
            byte_val = (data_value >> (i * 8)) & 0xFF
            beat_data.append(byte_val)
            
            # Get keep bit if available
            if self.tkeep:
                keep_value = int(self.tkeep.value)
                keep_bit = (keep_value >> i) & 1
                beat_keep.append(keep_bit)
            else:
                beat_keep.append(1)  # Default to all valid
                
        # Get other signal values
        user_val = int(self.tuser.value) if self.tuser else 0
        dest_val = int(self.tdest.value) if self.tdest else 0
        id_val = int(self.tid.value) if self.tid else 0
        last_val = bool(self.tlast.value) if self.tlast else False
        
        # Start new transaction if needed
        if self._current_transaction is None:
            self._current_transaction = []
            self._current_keep = []
            self._current_user = user_val
            self._current_dest = dest_val
            self._current_id = id_val
            
        # Add beat data to current transaction
        self._current_transaction.extend(beat_data)
        self._current_keep.extend(beat_keep)
        
        # Complete transaction if last beat
        if last_val:
            await self._complete_transaction()
            
    async def _complete_transaction(self) -> None:
        """Complete and emit the current transaction."""
        if self._current_transaction is None:
            return
            
        # Filter out invalid bytes based on keep signals
        valid_data = []
        for i, (data_byte, keep_bit) in enumerate(zip(self._current_transaction, self._current_keep)):
            if keep_bit:
                valid_data.append(data_byte)
                
        # Create transaction object
        timestamp = cocotb.utils.get_sim_time('ns')
        transaction = AxiStreamTransaction(
            data=valid_data,
            keep=self._current_keep[:len(valid_data)],
            last=True,
            user=self._current_user,
            dest=self._current_dest,
            id_val=self._current_id,
            timestamp=timestamp
        )
        
        # Store as last transaction and notify observers
        self._last_transaction = transaction
        self.notify_observers(transaction)
        
        self.logger.debug(f"Captured transaction: {len(valid_data)} bytes, "
                         f"user={self._current_user}, dest={self._current_dest}, id={self._current_id}")
        
        # Reset current transaction
        self._current_transaction = None
        self._current_keep = None
        
    async def _get_last_transaction(self) -> AxiStreamTransaction:
        """Get the most recently observed transaction."""
        if self._last_transaction:
            return self._last_transaction
        else:
            raise RuntimeError("No transactions observed yet")
            
    def get_transaction_stats(self) -> Dict[str, int]:
        """
        Get transaction statistics.
        
        Returns:
            Dictionary with transaction statistics
        """
        return {
            'transactions_observed': self.transactions_observed,
            'bytes_observed': sum(len(txn.data) for txn in self._get_all_transactions()),
        }
        
    def _get_all_transactions(self) -> List[AxiStreamTransaction]:
        """Get all observed transactions (for stats)."""
        # In a full implementation, we might store all transactions
        # For now, just return the last one if available
        return [self._last_transaction] if self._last_transaction else []
        
    async def wait_for_packet(self, timeout_cycles: Optional[int] = None) -> AxiStreamTransaction:
        """
        Wait for a complete packet (transaction with last=True).
        
        Args:
            timeout_cycles: Maximum cycles to wait
            
        Returns:
            Complete packet transaction
        """
        start_count = self.transactions_observed
        return await self.wait_for_transaction(timeout_cycles)
