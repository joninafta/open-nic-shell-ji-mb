"""
AXI Stream monitor for protocol compliance and data integrity checking.
Monitors both input and output AXI Stream interfaces.
"""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import time


@dataclass
class AxiStreamBeat:
    """Represents a single AXI Stream beat."""
    tdata: int
    tkeep: int
    tlast: bool
    tuser: int
    tvalid: bool
    tready: bool
    timestamp: float = field(default_factory=time.time)


@dataclass 
class AxiStreamPacket:
    """Represents a complete AXI Stream packet."""
    beats: List[AxiStreamBeat] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    
    @property
    def size_bytes(self) -> int:
        """Calculate packet size in bytes."""
        total_bytes = 0
        for beat in self.beats:
            if beat.tlast:
                # Count valid bytes in final beat using tkeep
                valid_bytes = bin(beat.tkeep).count('1')
                total_bytes += valid_bytes
            else:
                # All bytes valid in non-final beats
                bytes_per_beat = 64  # 512 bits / 8
                total_bytes += bytes_per_beat
        return total_bytes
        
    @property
    def data_bytes(self) -> bytes:
        """Extract packet data as bytes."""
        data = b''
        bytes_per_beat = 64  # 512 bits / 8
        
        for beat in self.beats:
            # Convert tdata to bytes (little-endian)
            beat_bytes = beat.tdata.to_bytes(bytes_per_beat, byteorder='little')
            
            if beat.tlast:
                # Only include valid bytes in final beat
                valid_bytes = bin(beat.tkeep).count('1')
                data += beat_bytes[:valid_bytes]
            else:
                data += beat_bytes
                
        return data


class AxiStreamMonitor:
    """Monitors AXI Stream interface for protocol compliance and packet capture."""
    
    def __init__(self, dut, clock, interface_name: str, signals: Dict[str, Any]):
        """
        Initialize AXI Stream monitor.
        
        Args:
            dut: Device under test handle
            clock: Clock signal
            interface_name: Name for this interface (e.g., "input", "output")
            signals: Dictionary mapping signal names to DUT signals
                    Expected keys: tvalid, tready, tdata, tkeep, tlast, tuser
        """
        self.dut = dut
        self.clock = clock
        self.name = interface_name
        self.signals = signals
        
        # Monitoring state
        self.packets: List[AxiStreamPacket] = []
        self.current_packet: Optional[AxiStreamPacket] = None
        self.total_beats = 0
        self.total_packets = 0
        
        # Protocol violation tracking
        self.protocol_violations: List[str] = []
        
        # Callbacks
        self.packet_callbacks: List[Callable[[AxiStreamPacket], None]] = []
        self.beat_callbacks: List[Callable[[AxiStreamBeat], None]] = []
        
        # Control
        self.monitoring = False
        
    def add_packet_callback(self, callback: Callable[[AxiStreamPacket], None]):
        """Add callback to be called when packet is complete."""
        self.packet_callbacks.append(callback)
        
    def add_beat_callback(self, callback: Callable[[AxiStreamBeat], None]):
        """Add callback to be called for each beat."""
        self.beat_callbacks.append(callback)
        
    async def start_monitoring(self):
        """Start monitoring the AXI Stream interface."""
        self.monitoring = True
        cocotb.log.info(f"Starting AXI Stream monitoring on {self.name}")
        
        # Start monitoring task
        cocotb.start_soon(self._monitor_interface())
        
    def stop_monitoring(self):
        """Stop monitoring the interface."""
        self.monitoring = False
        cocotb.log.info(f"Stopped AXI Stream monitoring on {self.name}")
        
    async def _monitor_interface(self):
        """Main monitoring loop."""
        while self.monitoring:
            await RisingEdge(self.clock)
            
            # Read current signal values
            tvalid = bool(self.signals['tvalid'].value)
            tready = bool(self.signals['tready'].value)
            
            if tvalid and tready:
                # Valid transaction
                beat = AxiStreamBeat(
                    tdata=int(self.signals['tdata'].value),
                    tkeep=int(self.signals['tkeep'].value),
                    tlast=bool(self.signals['tlast'].value),
                    tuser=int(self.signals['tuser'].value),
                    tvalid=tvalid,
                    tready=tready,
                    timestamp=time.time()
                )
                
                self._process_beat(beat)
                
    def _process_beat(self, beat: AxiStreamBeat):
        """Process a single AXI Stream beat."""
        self.total_beats += 1
        
        # Check for protocol violations
        self._check_protocol_compliance(beat)
        
        # Handle packet framing
        if self.current_packet is None:
            # Start new packet
            self.current_packet = AxiStreamPacket(start_time=beat.timestamp)
            
        self.current_packet.beats.append(beat)
        
        # Call beat callbacks
        for callback in self.beat_callbacks:
            try:
                callback(beat)
            except Exception as e:
                cocotb.log.error(f"Beat callback error: {e}")
                
        # Check for end of packet
        if beat.tlast:
            self.current_packet.end_time = beat.timestamp
            self.packets.append(self.current_packet)
            self.total_packets += 1
            
            # Call packet callbacks
            for callback in self.packet_callbacks:
                try:
                    callback(self.current_packet)
                except Exception as e:
                    cocotb.log.error(f"Packet callback error: {e}")
                    
            cocotb.log.debug(f"{self.name}: Completed packet #{self.total_packets}, "
                           f"size={self.current_packet.size_bytes} bytes")
            
            self.current_packet = None
            
    def _check_protocol_compliance(self, beat: AxiStreamBeat):
        """Check for AXI Stream protocol violations."""
        # Check tkeep validity
        if beat.tlast:
            # tkeep should be contiguous from LSB
            tkeep = beat.tkeep
            if tkeep != 0:
                # Find the position of the highest set bit
                highest_bit = tkeep.bit_length() - 1
                # Check if all bits below are set (contiguous from LSB)
                expected_mask = (1 << (highest_bit + 1)) - 1
                if tkeep != expected_mask:
                    violation = f"Non-contiguous tkeep on tlast: 0x{tkeep:016x}"
                    self.protocol_violations.append(violation)
                    cocotb.log.warning(f"{self.name}: {violation}")
                    
        # Check for tlast without tkeep
        if beat.tlast and beat.tkeep == 0:
            violation = "tlast asserted with tkeep=0"
            self.protocol_violations.append(violation)
            cocotb.log.warning(f"{self.name}: {violation}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'total_packets': self.total_packets,
            'total_beats': self.total_beats,
            'protocol_violations': len(self.protocol_violations),
            'violation_details': self.protocol_violations.copy()
        }
        
    def clear_statistics(self):
        """Clear all statistics and captured packets."""
        self.packets.clear()
        self.protocol_violations.clear()
        self.total_beats = 0
        self.total_packets = 0
        self.current_packet = None
        
    def wait_for_packet(self, timeout_cycles: int = 1000) -> AxiStreamPacket:
        """Wait for the next complete packet."""
        initial_count = self.total_packets
        
        async def _wait():
            for _ in range(timeout_cycles):
                await RisingEdge(self.clock)
                if self.total_packets > initial_count:
                    return self.packets[-1]
            raise TimeoutError(f"No packet received within {timeout_cycles} cycles")
            
        return cocotb.start_soon(_wait())
        
    def get_latest_packet(self) -> Optional[AxiStreamPacket]:
        """Get the most recently completed packet."""
        return self.packets[-1] if self.packets else None
        
    def verify_packet_integrity(self, expected_packet: bytes, received_packet: AxiStreamPacket) -> bool:
        """Verify that received packet data matches expected."""
        received_data = received_packet.data_bytes
        
        if len(expected_packet) != len(received_data):
            cocotb.log.error(f"Packet size mismatch: expected {len(expected_packet)}, "
                           f"received {len(received_data)}")
            return False
            
        if expected_packet != received_data:
            cocotb.log.error("Packet data mismatch")
            # Log first few differing bytes for debugging
            for i, (exp, rcv) in enumerate(zip(expected_packet, received_data)):
                if exp != rcv:
                    cocotb.log.error(f"Byte {i}: expected 0x{exp:02x}, received 0x{rcv:02x}")
                    if i >= 10:  # Limit output
                        cocotb.log.error("... (more differences)")
                        break
            return False
            
        return True


class AxiStreamDriver:
    """Drives AXI Stream interface with test packets."""
    
    def __init__(self, dut, clock, signals: Dict[str, Any]):
        """
        Initialize AXI Stream driver.
        
        Args:
            dut: Device under test handle
            clock: Clock signal  
            signals: Dictionary mapping signal names to DUT signals
                    Expected keys: tvalid, tready, tdata, tkeep, tlast, tuser
        """
        self.dut = dut
        self.clock = clock
        self.signals = signals
        
        # Initialize signals
        self.signals['tvalid'].value = 0
        self.signals['tdata'].value = 0
        self.signals['tkeep'].value = 0
        self.signals['tlast'].value = 0
        self.signals['tuser'].value = 0
        
    async def send_packet(self, packet_beats: List[tuple], inter_beat_delay: int = 0):
        """
        Send a packet as a sequence of AXI Stream beats.
        
        Args:
            packet_beats: List of (tdata, tkeep, tlast, tuser) tuples
            inter_beat_delay: Clock cycles to wait between beats
        """
        for i, (tdata, tkeep, tlast, tuser) in enumerate(packet_beats):
            # Wait for ready
            await self._wait_for_ready()
            
            # Drive signals
            self.signals['tvalid'].value = 1
            self.signals['tdata'].value = tdata
            self.signals['tkeep'].value = tkeep
            self.signals['tlast'].value = int(tlast)
            self.signals['tuser'].value = tuser
            
            # Wait for clock edge
            await RisingEdge(self.clock)
            
            # Add inter-beat delay if specified
            if inter_beat_delay > 0 and i < len(packet_beats) - 1:
                self.signals['tvalid'].value = 0
                for _ in range(inter_beat_delay):
                    await RisingEdge(self.clock)
                    
        # Deassert tvalid after packet
        self.signals['tvalid'].value = 0
        self.signals['tlast'].value = 0
        
    async def _wait_for_ready(self, timeout_cycles: int = 1000):
        """Wait for tready to be asserted."""
        for _ in range(timeout_cycles):
            await RisingEdge(self.clock)
            if bool(self.signals['tready'].value):
                return
        raise TimeoutError("tready not asserted within timeout")
        
    async def send_idle_cycles(self, cycles: int):
        """Send idle cycles (tvalid=0)."""
        self.signals['tvalid'].value = 0
        for _ in range(cycles):
            await RisingEdge(self.clock)
            
    async def apply_backpressure(self, pattern: List[bool]):
        """Apply backpressure pattern to tready (for monitor-side)."""
        # This would be used on the output side to simulate downstream backpressure
        for ready_val in pattern:
            self.signals['tready'].value = int(ready_val)
            await RisingEdge(self.clock)
