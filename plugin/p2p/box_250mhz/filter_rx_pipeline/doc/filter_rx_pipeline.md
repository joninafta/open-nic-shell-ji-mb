# Filter RX Pipeline Module

A configurable packet filtering pipeline that processes Ethernet frames containing
IPv4 or IPv6 packets. Implements a 2-stage pipeline with AXI Stream interfaces
for high-throughput packet processing.

## Features:
 - Configurable number of filter rules (NUM_RULES parameter)
 - IPv4/IPv6 destination IP and port matching
 - Priority-based rule matching (lower index = higher priority)
 - Packet statistics counters (total, dropped, per-rule hits)
 - Big-endian byte ordering support
 - Flow control with ready/valid handshaking

## Pipeline Stages

- **p0**: Input stage with header extraction and rule evaluation
- **p1**: Filtering decision stage
- **p2**: Output stage with filtered packets

## Parameters:
   NUM_RULES - Number of configurable filter rules (default: 2)

## Interfaces:
  s_axis_* - Slave AXI Stream interface (from adapter)
  m_axis_* - Master AXI Stream interface (to QDMA)
  cfg_reg  - Configuration register input for filter rules
  status_reg - Status register output with packet counters

