# OpenNIC Packet Filter Implementation

**Hash link:**
PR https://github.com/joninafta/open-nic-shell-ji-mb/commit/6f0396664b28d4b23d282e1445ef0ff4a59f0dbb
PR Fix https://github.com/joninafta/open-nic-shell-ji-mb/commit/d8b552b1df8aae5b3d7267432a4bd302633ab874

## Overview

This document describes the implementation of a packet filtering mechanism for the AMD OpenNIC project. The solution adds runtime-configurable packet filtering to the RX path, allowing users to define up to two filtering rules based on IP addresses and port numbers. Packets matching the configured criteria are transferred to host memory where their contents can be examined. Other packets will be dropped.
Several counters were added for telemetry.
The Host MMIO write to CSR is outside the scope of this assignment.
Writing the packets to host is not implemented as part of this assignemnt, but described later.

## 1. CSR

### Register Map

The packet filter module implements an AXI-Lite slave interface for configuration and monitoring. The register block is mapped to base address `0xB000` within the OpenNIC address space and provides 64 bytes of configuration and status registers.

**Configuration Registers:**
- **Rule 0 Configuration (0xB000-0xB014):**
  - `0xB000`: IPv4 destination address (0x0 = match any)
  - `0xB004-0xB010`: IPv6 destination address (128-bit, split across 4 registers)
  - `0xB014`: TCP/UDP destination port (0x0 = match any)

- **Rule 1 Configuration (0xB018-0xB02C):**
  - `0xB018`: IPv4 destination address
  - `0xB01C-0xB028`: IPv6 destination address (128-bit, split across 4 registers)
  - `0xB02C`: TCP/UDP destination port

**Status Registers (Read-Only):**
- `0xB030`: Rule 0 hit count - number of packets matched
- `0xB034`: Rule 1 hit count - number of packets matched
- `0xB038`: Total packet count - all packets processed
- `0xB03C`: Drop packet count - packets that didn't match any rule

### Expected Behavior

1. **Runtime Configuration:** Software can modify filtering rules at any time by writing to the configuration registers via AXI-Lite interface
2. **Packet Processing:** Each incoming packet is compared against both rules simultaneously
3. **Match Logic:** A packet matches if it satisfies the configured IP address AND port criteria for at least one rule
4. **Forwarding:** Matching packets continue through the normal RX path to host memory
5. **Statistics:** Hardware maintains counters for monitoring filter performance

## 2. Filter block High-Level Design Description

### Architecture Overview

The packet filter is implemented as a pipeline stage inserted into the OpenNIC RX data path within the 250MHz user box. The design maintains the existing AXI-Stream interfaces while adding filtering capability and configuration registers.

### Filter Pipeline Description

#### filter_rx_pipeline (Top Module)
**Location:** `plugin/p2p/box_250mhz/filter_rx_pipeline/src/filter_rx_pipeline.sv`

**I/O Interfaces:**
- AXI-Stream RX input (512-bit data, 250MHz)
- AXI-Stream RX output (512-bit data, 250MHz) 
- AXI-Lite configuration interface (32-bit)
- Clock and reset signals

**Pipeline Stage 1 - Packet Parsing:**
The first stage of the filter pipeline extracts relevant fields from incoming Ethernet frames as they stream through the AXI-Stream interface. This stage identifies whether packets are IPv4 or IPv6, extracts destination IP addresses from the appropriate header fields, identifies TCP/UDP protocols, and extracts destination port numbers. The parsing logic operates on the 512-bit data width and handles packet boundaries using the AXI-Stream TLAST and TKEEP signals.

**Pipeline Stage 2 - Filter Logic:**
The second stage implements the core filtering functionality by comparing the parsed packet fields against the two configured rules simultaneously. Each rule supports wildcard matching where 0x0 values match any packet field. The filter generates match/drop decisions and updates internal statistics counters for rule hits, total packets processed, and dropped packets. This stage maintains full throughput by making filtering decisions within a single clock cycle.

**Pipeline Stage 3 - Output Control:**
The final stage handles packet forwarding decisions and AXI-Stream flow control. Packets that match at least one configured rule are forwarded to the output AXI-Stream interface unchanged, while non-matching packets are dropped. The stage also provides the AXI-Lite configuration interface for runtime rule updates and statistics access.

### Changes to OpenNIC Shell

**Box 250MHz Integration:**
- Modified `plugin/p2p/box_250mhz/box_250mhz.sv` to instantiate the filter_rx_pipeline module
- Connected filter module between existing RX packet adapter and user logic
- Added AXI-Lite interface connection to the configuration bus

**Address Map Updates:**
- Reserved address space `0xB000-0xB03F` for packet filter registers
- Updated system address decoder to route filter configuration traffic

### Host Memory Write Implementation Strategy

For transferring filtered packets to host memory, the current implementation leverages the existing QDMA infrastructure. However, for a more optimized approach in future versions, a dedicated DMA engine could be implemented using a ring buffer architecture.

The ring buffer approach would work as follows: The FPGA maintains a write pointer while the host maintains a read pointer (with a copy stored in MMIO registers). When writing a packet, the FPGA advances the write pointer. When the host consumes a packet, it advances the read pointer. The host must never attempt to read past the write pointer, and the FPGA knows the buffer is full when the write pointer would wrap around to equal the read pointer plus one.

This mechanism provides efficient flow control - before starting to write a packet, the FPGA checks that sufficient space exists in the host memory buffer. If the buffer is full, additional packets are dropped until space becomes available. This approach minimizes latency compared to traditional DMA request/response mechanisms while providing backpressure handling for sustainable operation under high packet rates.

The ring buffer implementation would require careful consideration of memory barriers and cache coherency, particularly on x86 platforms where the host may cache the read pointer value. Proper synchronization ensures that the FPGA sees updated read pointer values promptly, preventing unnecessary packet drops due to stale buffer status information.

## 3. Code and Simulation Repository
https://github.com/joninafta/open-nic-shell-ji-mb


**Key Directories:**
- `plugin/p2p/box_250mhz/filter_rx_pipeline/` - RTL implementation
- `plugin/p2p/box_250mhz/csr`- CSR implementation