# Filter RX Pipeline Module

A configurable packet filtering pipeline that processes AXI Stream packets and forwards only those matching specified IPv4/IPv6 address and port rules. Implements a 2-stage pipeline with header validation and rule matching logic.

## Features

- Configurable number of filter rules via NUM_RULES parameter
- Support for IPv4 and IPv6 packet filtering
- Source IP address and port-based filtering
- Header validation using tkeep signals
- Packet statistics counters (total, dropped, rule hits)
- Priority-based rule matching (lower index = higher priority)

## Pipeline Stages

- **p0**: Input stage with header extraction and rule evaluation
- **p1**: Filtering decision stage
- **p2**: Output stage with filtered packets

## Assumptions

- Ethernet packets without VLAN tags
- Big-endian byte ordering
- Complete packet headers within first AXI beat (ignoring tkeep)
