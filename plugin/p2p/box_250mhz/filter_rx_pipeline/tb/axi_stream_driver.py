"""
AXI Stream Driver and Monitor for cocotb testbenches

Provides high-level interfaces for driving and monitoring AXI Stream interfaces
"""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.binary import BinaryValue
import logging

logger = logging.getLogger(__name__)

class AXIStreamDriver:
    """Driver for AXI Stream slave interface"""
    
    def __init__(self, dut, prefix, clock):
        self.dut = dut
        self.clock = clock
        
        # Get signal references
        self.tvalid = getattr(dut, f"{prefix}_tvalid")
        self.tdata = getattr(dut, f"{prefix}_tdata") 
        self.tkeep = getattr(dut, f"{prefix}_tkeep")
        self.tlast = getattr(dut, f"{prefix}_tlast")
        self.tuser = getattr(dut, f"{prefix}_tuser")
        self.tready = getattr(dut, f"{prefix}_tready")
        
        # Initialize signals
        self.tvalid.value = 0
        self.tdata.value = 0
        self.tkeep.value = 0
        self.tlast.value = 0
        self.tuser.value = 0
        
    async def send_packet(self, packet_data: bytes):
        """Send a packet over AXI Stream interface"""
        logger.debug(f"Sending packet of {len(packet_data)} bytes")
        
        # Convert packet to list of 64-byte beats
        beats = self._packet_to_beats(packet_data)
        
        for i, (data, keep, last) in enumerate(beats):
            # Wait for ready
            while True:
                await RisingEdge(self.clock)
                if self.tready.value == 1:
                    break
                    
            # Drive signals
            self.tvalid.value = 1
            self.tdata.value = data
            self.tkeep.value = keep
            self.tlast.value = last
            self.tuser.value = 0  # Not used in this design
            
            logger.debug(f"Beat {i}: data=0x{data:0128x}, keep=0x{keep:016x}, last={last}")
            
        # Wait one more cycle then deassert
        await RisingEdge(self.clock)
        self.tvalid.value = 0
        self.tdata.value = 0
        self.tkeep.value = 0
        self.tlast.value = 0
        
    def _packet_to_beats(self, packet_data: bytes):
        """Convert packet data to AXI Stream beats (512-bit data, 64-bit keep)"""
        beats = []
        bytes_per_beat = 64  # 512 bits / 8 = 64 bytes
        
        # Pad packet to multiple of beat size
        padded_length = ((len(packet_data) + bytes_per_beat - 1) // bytes_per_beat) * bytes_per_beat
        padded_data = packet_data + b'\x00' * (padded_length - len(packet_data))
        
        for i in range(0, len(padded_data), bytes_per_beat):
            beat_data = padded_data[i:i + bytes_per_beat]
            
            # Convert to integer (big-endian)
            data_int = int.from_bytes(beat_data, byteorder='big')
            
            # Calculate keep (valid bytes in this beat)
            remaining_bytes = len(packet_data) - i
            if remaining_bytes >= bytes_per_beat:
                keep_bytes = bytes_per_beat
            else:
                keep_bytes = remaining_bytes
                
            # Keep mask (1 bit per byte, MSB first)
            keep_mask = (1 << keep_bytes) - 1
            keep_mask <<= (bytes_per_beat - keep_bytes)  # Shift to MSB
            
            # Last beat?
            is_last = (i + bytes_per_beat >= len(padded_data))
            
            beats.append((data_int, keep_mask, 1 if is_last else 0))
            
        return beats

class AXIStreamMonitor:
    """Monitor for AXI Stream master interface"""
    
    def __init__(self, dut, prefix, clock):
        self.dut = dut
        self.clock = clock
        
        # Get signal references
        self.tvalid = getattr(dut, f"{prefix}_tvalid")
        self.tdata = getattr(dut, f"{prefix}_tdata")
        self.tkeep = getattr(dut, f"{prefix}_tkeep")
        self.tlast = getattr(dut, f"{prefix}_tlast")
        self.tuser = getattr(dut, f"{prefix}_tuser")
        self.tready = getattr(dut, f"{prefix}_tready")
        
        # Set ready signal
        self.tready.value = 1
        
        # Received packets
        self.received_packets = []
        
        # Start monitoring
        cocotb.start_soon(self._monitor())
        
    async def _monitor(self):
        """Monitor AXI Stream transactions"""
        current_packet = []
        
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()  # Wait for signals to settle
            
            if self.tvalid.value == 1 and self.tready.value == 1:
                # Valid transaction
                data = int(self.tdata.value)
                keep = int(self.tkeep.value)
                last = int(self.tlast.value)
                
                # Extract valid bytes from this beat
                beat_bytes = self._beat_to_bytes(data, keep)
                current_packet.extend(beat_bytes)
                
                logger.debug(f"Monitor beat: data=0x{data:0128x}, keep=0x{keep:016x}, last={last}")
                
                if last == 1:
                    # End of packet
                    packet_data = bytes(current_packet)
                    self.received_packets.append(packet_data)
                    logger.debug(f"Monitor received packet of {len(packet_data)} bytes")
                    current_packet = []
                    
    def _beat_to_bytes(self, data: int, keep: int):
        """Convert AXI Stream beat to bytes"""
        bytes_per_beat = 64
        beat_bytes = []
        
        # Convert data to bytes (big-endian)
        data_bytes = data.to_bytes(bytes_per_beat, byteorder='big')
        
        # Extract valid bytes based on keep mask
        for i in range(bytes_per_beat):
            if keep & (1 << (bytes_per_beat - 1 - i)):  # MSB first
                beat_bytes.append(data_bytes[i])
            else:
                break  # Stop at first invalid byte
                
        return beat_bytes
        
    async def wait_for_packet(self, timeout_cycles: int = 1000):
        """Wait for a packet to be received"""
        initial_count = len(self.received_packets)
        
        for _ in range(timeout_cycles):
            await RisingEdge(self.clock)
            if len(self.received_packets) > initial_count:
                return self.received_packets[-1]
                
        return None  # Timeout
        
    def get_received_packets(self):
        """Get all received packets"""
        return self.received_packets.copy()
        
    def clear_received_packets(self):
        """Clear received packet buffer"""
        self.received_packets.clear()

class AXIStreamSink:
    """Simple AXI Stream sink that accepts all data"""
    
    def __init__(self, dut, prefix, clock, ready_prob: float = 1.0):
        self.dut = dut
        self.clock = clock
        self.ready_prob = ready_prob
        
        # Get ready signal
        self.tready = getattr(dut, f"{prefix}_tready")
        
        # Start ready generation
        cocotb.start_soon(self._generate_ready())
        
    async def _generate_ready(self):
        """Generate ready signal with specified probability"""
        import random
        
        while True:
            await RisingEdge(self.clock)
            if random.random() < self.ready_prob:
                self.tready.value = 1
            else:
                self.tready.value = 0

class AXIStreamSource:
    """Simple AXI Stream source for generating traffic"""
    
    def __init__(self, dut, prefix, clock):
        self.dut = dut
        self.clock = clock
        
        # Get signal references
        self.tvalid = getattr(dut, f"{prefix}_tvalid")
        self.tdata = getattr(dut, f"{prefix}_tdata")
        self.tkeep = getattr(dut, f"{prefix}_tkeep")
        self.tlast = getattr(dut, f"{prefix}_tlast")
        self.tuser = getattr(dut, f"{prefix}_tuser")
        self.tready = getattr(dut, f"{prefix}_tready")
        
        # Initialize
        self.tvalid.value = 0
        self.tdata.value = 0
        self.tkeep.value = 0
        self.tlast.value = 0
        self.tuser.value = 0
        
    async def send_random_data(self, num_beats: int):
        """Send random data for testing"""
        import random
        
        for i in range(num_beats):
            # Wait for ready
            while True:
                await RisingEdge(self.clock)
                if self.tready.value == 1:
                    break
                    
            # Generate random data
            data = random.randint(0, (1 << 512) - 1)
            keep = (1 << 64) - 1  # All bytes valid
            last = 1 if i == num_beats - 1 else 0
            
            self.tvalid.value = 1
            self.tdata.value = data
            self.tkeep.value = keep
            self.tlast.value = last
            
        # Deassert after last beat
        await RisingEdge(self.clock)
        self.tvalid.value = 0
