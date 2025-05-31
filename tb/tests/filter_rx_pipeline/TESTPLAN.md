# Filter RX Pipeline - Verification Testplan

**Document Version**: 1.0  
**Last Updated**: May 29, 2025  
**Status**: Active Development  
**Module**: `filter_rx_pipeline`  
**Location**: `plugin/p2p/box_250mhz/filter_rx_pipeline/`

---

## 1. Module Overview

### 1.1 Description
The Filter RX Pipeline is a configurable packet filtering module that processes Ethernet frames containing IPv4 or IPv6 packets. It implements a 2-stage pipeline with AXI Stream interfaces for high-throughput packet processing at 250MHz clock domain.

### 1.2 Key Features
- **Configurable Rules**: Support for NUM_RULES filter rules (default: 2)
- **Protocol Support**: IPv4 and IPv6 packet filtering
- **Matching Criteria**: Destination IP address and port-based filtering
- **Priority Handling**: Rule priority based on index (lower index = higher priority)
- **Statistics**: Packet counters for total, dropped, and per-rule hits
- **Flow Control**: Full AXI Stream ready/valid handshaking
- **Pipeline**: 2-stage pipeline (p1/p2) for high-throughput processing

### 1.3 Interfaces

| Interface | Type | Width | Description |
|-----------|------|-------|-------------|
| `s_axis_*` | AXI Stream Slave | 512-bit data | Input from packet adapter |
| `m_axis_*` | AXI Stream Master | 512-bit data | Output to QDMA subsystem |
| `cfg_reg` | Configuration | 384-bit | Filter rules configuration |
| `status_reg` | Status | 128-bit | Packet statistics output |
| `aclk` | Clock | 1-bit | 250MHz system clock |
| `aresetn` | Reset | 1-bit | Active-low reset |

---

## 2. Verification Strategy

### 2.1 Verification Approach
- **Constrained Random Testing**: Generate diverse packet scenarios
- **Directed Testing**: Specific corner cases and protocol compliance
- **Coverage-Driven Verification**: Ensure all features are exercised
- **Self-Checking**: Automated result verification with scoreboards
- **Performance Testing**: Throughput and latency characterization

### 2.2 Verification Environment
- **Framework**: Cocotb with Python-based testbench
- **Simulator**: Verilator (primary), Questa/Xcelium (secondary)
- **Language**: SystemVerilog DUT with Python verification
- **Coverage**: Functional and code coverage collection

---

## 3. Test Categories

### 3.1 Basic Functionality Tests

#### 3.1.1 IPv4 Packet Filtering
**Test ID**: `test_ipv4_basic_filtering`  
**Priority**: High  
**Description**: Verify basic IPv4 packet filtering functionality

**Test Scenarios**:
- Configure Rule 0: IPv4 address = 192.168.1.1, Port = 80
- Configure Rule 1: IPv4 address = 192.168.1.2, Port = 443
- Send IPv4 packets matching Rule 0 → Verify forwarded
- Send IPv4 packets matching Rule 1 → Verify forwarded  
- Send IPv4 packets not matching any rule → Verify dropped
- Verify rule priority (Rule 0 has higher priority than Rule 1)

**Expected Results**:
- Matching packets pass through with correct rule_hit indication
- Non-matching packets are dropped
- Statistics counters increment correctly
- No protocol violations on AXI Stream interfaces

#### 3.1.2 IPv6 Packet Filtering
**Test ID**: `test_ipv6_basic_filtering`  
**Priority**: High  
**Description**: Verify basic IPv6 packet filtering functionality

**Test Scenarios**:
- Configure Rule 0: IPv6 address = 2001:db8::1, Port = 80
- Configure Rule 1: IPv6 address = 2001:db8::2, Port = 443
- Send IPv6 packets with matching destination addresses
- Send IPv6 packets with non-matching addresses
- Verify port matching for UDP/TCP packets

**Expected Results**:
- IPv6 packets filtered correctly based on destination IP and port
- Statistics reflect IPv6 packet processing
- Proper handling of 128-bit IPv6 addresses

#### 3.1.3 Mixed Protocol Testing
**Test ID**: `test_mixed_protocol_filtering`  
**Priority**: Medium  
**Description**: Test filtering with mixed IPv4 and IPv6 traffic

**Test Scenarios**:
- Configure rules for both IPv4 and IPv6 addresses
- Send interleaved IPv4 and IPv6 packets
- Verify both protocols handled correctly
- Test rule priority across different protocols

### 3.2 Configuration Tests

#### 3.2.1 Rule Configuration
**Test ID**: `test_rule_configuration`  
**Priority**: High  
**Description**: Verify rule configuration functionality

**Test Scenarios**:
- Configure all available rules (0 to NUM_RULES-1)
- Test configuration during active packet processing
- Verify rule field parsing (IPv4/IPv6 addresses, ports)
- Test wildcard port configuration (port = 0)

#### 3.2.2 Dynamic Reconfiguration  
**Test ID**: `test_dynamic_reconfiguration`  
**Priority**: Medium  
**Description**: Test rule changes during operation

**Test Scenarios**:
- Start with initial rule set
- Send matching packets → verify pass
- Change rules dynamically
- Send same packets → verify new behavior
- Ensure no in-flight packets corrupted

### 3.3 Protocol Compliance Tests

#### 3.3.1 AXI Stream Compliance
**Test ID**: `test_axi_stream_compliance`  
**Priority**: High  
**Description**: Verify AXI Stream protocol compliance

**Test Scenarios**:
- Test back-pressure handling (m_axis_tready deassertion)
- Verify tvalid/tready handshaking
- Test tkeep handling for partial beats
- Verify tlast alignment and packet boundaries
- Test tuser signal pass-through

#### 3.3.2 Packet Integrity
**Test ID**: `test_packet_integrity`  
**Priority**: High  
**Description**: Ensure packet data integrity through pipeline

**Test Scenarios**:
- Send packets with known data patterns
- Verify output data matches input exactly
- Test various packet sizes (64B to 9KB)
- Verify no data corruption in pipeline stages

### 3.4 Edge Cases and Corner Cases

#### 3.4.1 Malformed Packets
**Test ID**: `test_malformed_packets`  
**Priority**: Medium  
**Description**: Handle malformed or unexpected packets

**Test Scenarios**:
- Send non-Ethernet frames
- Send truncated packets (early tlast)
- Send packets with invalid EtherType
- Send packets with corrupted headers
- Verify graceful handling without hangs

#### 3.4.2 Boundary Conditions
**Test ID**: `test_boundary_conditions`  
**Priority**: Medium  
**Description**: Test boundary and limit conditions

**Test Scenarios**:
- Minimum packet size (64 bytes)
- Maximum packet size (9KB)  
- Back-to-back packets with no gap
- Single-beat packets (tvalid + tlast same cycle)
- Empty packets (only headers)

### 3.5 Performance Tests

#### 3.5.1 Throughput Testing
**Test ID**: `test_max_throughput`  
**Priority**: High  
**Description**: Verify maximum throughput capability

**Test Scenarios**:
- Send continuous packet stream at line rate
- Measure sustained throughput
- Verify no packet drops under full load
- Test with various packet sizes

**Performance Targets**:
- **Line Rate**: 100 Gbps (250MHz × 512-bit)
- **Latency**: ≤ 3 clock cycles for pipeline
- **Packet Rate**: > 148 Mpps (64-byte packets)

#### 3.5.2 Stress Testing
**Test ID**: `test_stress_scenarios`  
**Priority**: Medium  
**Description**: Extended stress testing

**Test Scenarios**:
- Continuous operation for 1M+ packets
- Random back-pressure injection
- Rule configuration changes under load
- Memory leak detection (if applicable)

### 3.6 Statistics and Monitoring

#### 3.6.1 Counter Verification
**Test ID**: `test_statistics_counters`  
**Priority**: High  
**Description**: Verify statistics counter accuracy

**Test Scenarios**:
- Send known number of packets per category
- Verify total_packets counter
- Verify dropped_packets counter  
- Verify per-rule hit counters (rule0_hit_count, rule1_hit_count)
- Test counter overflow behavior

#### 3.6.2 Debug Features
**Test ID**: `test_debug_features`  
**Priority**: Low  
**Description**: Verify debug and diagnostic features

**Test Scenarios**:
- Verify debug print statements in simulation
- Test packet tracing capabilities
- Verify rule match debug information

---

## 4. Coverage Plan

### 4.1 Functional Coverage

#### 4.1.1 Protocol Coverage
- **IPv4 Packets**: Various source/destination combinations
- **IPv6 Packets**: Various IPv6 address formats
- **Mixed Traffic**: IPv4/IPv6 interleaved scenarios
- **Port Coverage**: TCP/UDP port ranges, wildcard ports

#### 4.1.2 Rule Coverage
- **Rule Utilization**: Each rule hit at least once
- **Rule Priority**: Lower-index rules override higher-index
- **Rule Combinations**: Multiple rules matching same packet
- **Configuration States**: All rule configuration combinations

#### 4.1.3 Packet Size Coverage
- **Minimum**: 64-byte packets
- **Maximum**: 9KB jumbo frames
- **Distribution**: Uniform distribution across size ranges
- **Boundary**: Powers of 2, odd sizes, random sizes

#### 4.1.4 Flow Control Coverage
- **Back-pressure**: Various ready/valid patterns
- **Pipeline Stages**: All pipeline stages exercised
- **Packet Boundaries**: Single-beat and multi-beat packets

### 4.2 Code Coverage Targets
- **Line Coverage**: ≥ 95%
- **Branch Coverage**: ≥ 90%
- **Expression Coverage**: ≥ 85%
- **Toggle Coverage**: ≥ 80%

---

## 5. Test Implementation

### 5.1 Test Structure
```
tb/tests/filter_rx_pipeline/
├── test_filter_basic.py           # Main test collection
├── test_filter_protocol.py        # Protocol-specific tests
├── test_filter_performance.py     # Performance tests
├── test_filter_coverage.py        # Coverage-driven tests
├── configs/
│   ├── ipv4_rules.yaml            # IPv4 test configurations
│   ├── ipv6_rules.yaml            # IPv6 test configurations
│   └── stress_test.yaml           # Stress test parameters
└── utils/
    ├── packet_generators.py       # Packet generation utilities
    ├── filter_checkers.py         # Response checking
    └── coverage_collectors.py     # Coverage utilities
```

### 5.2 Test Configuration Examples

#### 5.2.1 Basic IPv4 Configuration
```yaml
filter_config:
  num_rules: 2
  rules:
    - rule_id: 0
      ipv4_addr: 0xC0A80101      # 192.168.1.1
      ipv6_addr: 0x0             # Unused for IPv4
      port: 80                   # HTTP
    - rule_id: 1  
      ipv4_addr: 0xC0A80102      # 192.168.1.2
      ipv6_addr: 0x0             # Unused for IPv4
      port: 443                  # HTTPS
```

#### 5.2.2 Mixed Protocol Configuration
```yaml
filter_config:
  num_rules: 2
  rules:
    - rule_id: 0
      ipv4_addr: 0xC0A80101                           # 192.168.1.1
      ipv6_addr: 0x0                                  # Unused
      port: 80
    - rule_id: 1
      ipv4_addr: 0x0                                  # Unused  
      ipv6_addr: 0x20010db8000000000000000000000001    # 2001:db8::1
      port: 443
```

### 5.3 Packet Generation Strategy

#### 5.3.1 IPv4 Packet Templates
- **Basic UDP**: Ethernet + IPv4 + UDP headers
- **Basic TCP**: Ethernet + IPv4 + TCP headers  
- **Various Sizes**: 64B to 1518B standard frames
- **Jumbo Frames**: Up to 9KB for jumbo frame testing

#### 5.3.2 IPv6 Packet Templates  
- **Basic UDP**: Ethernet + IPv6 + UDP headers
- **Basic TCP**: Ethernet + IPv6 + TCP headers
- **Extension Headers**: Test IPv6 with various extension headers

### 5.4 Verification Components

#### 5.4.1 Drivers
- **AxiStreamDriver**: Generate AXI Stream transactions
- **FilterConfigDriver**: Configure filter rules
- **ClockDriver**: Generate 250MHz clock

#### 5.4.2 Monitors  
- **AxiStreamMonitor**: Monitor input/output AXI Stream
- **FilterStatsMonitor**: Monitor statistics registers
- **ProtocolMonitor**: Check protocol compliance

#### 5.4.3 Scoreboards
- **FilterScoreboard**: Verify filtering decisions
- **PacketScoreboard**: Check packet integrity
- **StatsScoreboard**: Verify counter accuracy

---

## 6. Test Execution Plan

### 6.1 Test Phases

#### Phase 1: Basic Functionality (Week 1)
- IPv4 basic filtering tests
- IPv6 basic filtering tests  
- Configuration tests
- **Exit Criteria**: All basic tests pass, >80% code coverage

#### Phase 2: Protocol Compliance (Week 2)
- AXI Stream compliance tests
- Packet integrity tests
- Edge case handling
- **Exit Criteria**: All protocol tests pass, >90% code coverage

#### Phase 3: Performance & Stress (Week 3)
- Throughput testing
- Stress testing  
- Performance characterization
- **Exit Criteria**: Meet performance targets, sustained operation

#### Phase 4: Coverage Closure (Week 4)
- Coverage-driven test generation
- Corner case exploration
- Final verification
- **Exit Criteria**: >95% code coverage, all functional coverage bins hit

### 6.2 Regression Testing
- **Nightly Regression**: All basic functionality tests
- **Weekly Regression**: Complete test suite including stress tests
- **Release Regression**: Full test suite with multiple seeds

### 6.3 Pass/Fail Criteria

#### 6.3.1 Functional Criteria
- All directed tests pass
- No protocol violations detected
- Statistics counters accurate
- No data corruption observed

#### 6.3.2 Performance Criteria  
- Sustained line rate throughput
- Pipeline latency ≤ 3 cycles
- No packet drops under normal operation

#### 6.3.3 Coverage Criteria
- Line coverage ≥ 95%
- Functional coverage bins ≥ 90% hit
- All protocol combinations tested

---

## 7. Known Issues and Limitations

### 7.1 Current Limitations
- **VLAN Support**: No VLAN tag support in current implementation
- **Rule Count**: Fixed at compile time (NUM_RULES parameter)
- **Protocol Support**: Limited to IPv4/IPv6, no other protocols

### 7.2 Future Enhancements
- **VLAN Awareness**: Support for 802.1Q VLAN tags
- **Dynamic Rules**: Runtime rule count configuration
- **Additional Protocols**: MPLS, other Layer 3 protocols
- **Advanced Filtering**: Layer 4 protocol-specific filtering

---

## 8. Test Results and Metrics

### 8.1 Test Execution Summary
*To be updated during test execution*

| Test Category | Total Tests | Passed | Failed | Coverage |
|---------------|-------------|--------|--------|----------|
| Basic Functionality | TBD | TBD | TBD | TBD |
| Protocol Compliance | TBD | TBD | TBD | TBD |
| Performance | TBD | TBD | TBD | TBD |
| **Total** | **TBD** | **TBD** | **TBD** | **TBD** |

### 8.2 Performance Results
*To be updated after performance testing*

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Throughput (Gbps) | 100 | TBD | TBD |
| Latency (cycles) | ≤ 3 | TBD | TBD |
| Packet Rate (Mpps) | > 148 | TBD | TBD |

---

## 9. References

1. **Filter RX Pipeline RTL**: `plugin/p2p/box_250mhz/filter_rx_pipeline/src/filter_rx_pipeline.sv`
2. **Module Documentation**: `plugin/p2p/box_250mhz/filter_rx_pipeline/doc/filter_rx_pipeline.md`
3. **Configuration Package**: `plugin/p2p/box_250mhz/common/cfg_reg_pkg.sv`
4. **Packet Package**: `plugin/p2p/box_250mhz/common/packet_pkg.sv`
5. **OpenNIC Shell Architecture**: `tb/REQ.md`
6. **AXI Stream Standard**: ARM AMBA AXI4-Stream Protocol Specification

---

**Document Approval**:
- [ ] Design Engineer Review
- [ ] Verification Engineer Review  
- [ ] Project Manager Approval
- [ ] Final Sign-off

*End of Filter RX Pipeline Testplan*
