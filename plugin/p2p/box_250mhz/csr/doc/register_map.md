# Filter RX Pipeline Register Map

## Overview

The Filter RX Pipeline module implements an AXI-Lite slave interface for configuration and status monitoring. The register block provides configuration for packet filtering rules and read-only status counters.

## Register Block Structure

- **Base Address**: Configurable via `REG_PREFIX` parameter (default: `0xB000`)
- **Address Width**: 12 bits (4KB address space)
- **Data Width**: 32 bits
- **Total Registers**: 16 registers (64 bytes)

## Configuration Registers

The module supports 2 filtering rules, each containing:
- IPv4 address (32 bits)
- IPv6 address (128 bits, split across 4 registers)
- Port number (32 bits)

## Register Map Table

| Offset | Name | Type | Description |
|--------|------|------|-------------|
| 0x000 | RULE0_IPV4 | R/W | Rule 0: IPv4 destination address (0x0 = match any) |
| 0x004 | RULE0_IPV6_0 | R/W | Rule 0: IPv6 destination address bits [31:0] |
| 0x008 | RULE0_IPV6_1 | R/W | Rule 0: IPv6 destination address bits [63:32] |
| 0x00C | RULE0_IPV6_2 | R/W | Rule 0: IPv6 destination address bits [95:64] |
| 0x010 | RULE0_IPV6_3 | R/W | Rule 0: IPv6 destination address bits [127:96] |
| 0x014 | RULE0_PORT | R/W | Rule 0: TCP/UDP destination port (0x0 = match any) |
| 0x018 | RULE1_IPV4 | R/W | Rule 1: IPv4 destination address (0x0 = match any) |
| 0x01C | RULE1_IPV6_0 | R/W | Rule 1: IPv6 destination address bits [31:0] |
| 0x020 | RULE1_IPV6_1 | R/W | Rule 1: IPv6 destination address bits [63:32] |
| 0x024 | RULE1_IPV6_2 | R/W | Rule 1: IPv6 destination address bits [95:64] |
| 0x028 | RULE1_IPV6_3 | R/W | Rule 1: IPv6 destination address bits [127:96] |
| 0x02C | RULE1_PORT | R/W | Rule 1: TCP/UDP destination port (0x0 = match any) |
| 0x030 | RULE0_HIT_COUNT | R | Number of packets that matched Rule 0 |
| 0x034 | RULE1_HIT_COUNT | R | Number of packets that matched Rule 1 |
| 0x038 | TOTAL_PKT_COUNT | R | Total number of packets processed |
| 0x03C | DROP_PKT_COUNT | R | Number of packets dropped (no rule match) |

```
