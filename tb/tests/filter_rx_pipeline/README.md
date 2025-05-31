# Filter RX Pipeline

## Status

<!-- CI/CD Badges -->
![Tests](https://img.shields.io/badge/tests-unknown-lightgrey)
![Build](https://img.shields.io/badge/build-unknown-lightgrey)
![Simulator](https://img.shields.io/badge/simulator-verilator-blue)
<!-- End CI/CD Badges -->

## Overview

The `filter_rx_pipeline` module is a configurable packet filtering system designed for high-performance network processing. It processes Ethernet frames containing IPv4 or IPv6 packets using AXI Stream interfaces at 250MHz, providing rule-based filtering with comprehensive statistics tracking.

### Key Features

- ✅ **IPv4 and IPv6 Support**: Filters both IPv4 and IPv6 packets with configurable rules
- ✅ **High Performance**: Operates at 250MHz with 512-bit AXI Stream interfaces
- ✅ **Rule-Based Filtering**: Configurable filtering rules with priority support
- ✅ **Dynamic Reconfiguration**: Runtime rule updates without stopping traffic
- ✅ **Statistics Tracking**: Comprehensive packet and byte counters
- ✅ **Protocol Compliance**: Full AXI Stream protocol compliance
- ✅ **Error Handling**: Robust handling of malformed packets and edge cases

This testbench provides comprehensive verification including:

- **28 test cases** covering all functionality
- Stress testing with high packet rates  
- Coverage-driven verification
- Filter rule configuration and validation
- AXI Stream interface compliance
- Performance benchmarking
- CI/CD automated testing

## Structure

```
tb/tests/filter_rx_pipeline/
├── 📋 Test Planning Documents
│   ├── README.md                      # This file
│   ├── TESTPLAN.md                    # Master test plan
│   ├── TESTCASES.md                   # Detailed test cases
│   └── IMPLEMENTATION_SUMMARY.md     # Implementation details
│
├── 🧪 Test Implementation Files
│   ├── test_filter_basic.py           # Basic filtering functionality
│   ├── test_filter_config.py          # Configuration and dynamic tests
│   ├── test_filter_edge.py           # Edge cases and error handling
│   ├── test_filter_performance.py    # Performance and throughput tests
│   ├── test_filter_protocol.py       # Protocol compliance tests
│   └── test_filter_stats.py          # Statistics verification tests
│
├── 🛠️ Test Infrastructure
│   ├── tb_filter_rx_pipeline.sv      # SystemVerilog testbench wrapper
│   ├── Makefile                      # Build and run targets
│   ├── utils/
│   │   ├── test_utils.py             # Core testbench utilities
│   │   ├── packet_generator.py       # Scapy-based packet generation
│   │   ├── axi_stream_monitor.py     # AXI Stream protocol monitoring
│   │   └── statistics_checker.py     # Statistics counter verification
│   │
├── 🚀 CI/CD Integration
│   ├── run_ci_tests.sh              # Local CI/CD test runner
│   ├── generate_badges.py           # Status badge generator
│   ├── validate_tests.py            # Test validation utility
│   ├── setup_test_env.sh            # Environment setup script
│   ├── requirements.txt             # Python dependencies
│   └── .ci_config.yml              # CI/CD configuration
└── 📊 Results and Artifacts
    └── results/                      # Test results and logs
```

## Dependencies

- **Cocotb ≥1.8.0**: Python-based verification framework
- **Scapy ≥2.5.0**: Packet generation and manipulation
- **pytest ≥7.0.0**: Test framework
- **PyYAML ≥6.0**: Configuration file parsing
- **NumPy ≥1.21.0**: Numerical computations
- **Simulator**: Verilator (default), Questa, Xcelium, or VCS

### System Requirements
- **Python 3.9+**
- **Build tools**: `build-essential` (Linux), Xcode Command Line Tools (macOS)
- **Git**: For version control and CI/CD integration

## Quick Start

### 1. Environment Setup

```bash
# Navigate to test directory
cd tb/tests/filter_rx_pipeline

# Set up Python environment and dependencies
./setup_test_env.sh

# Validate installation
python3 validate_tests.py
```

### 2. Basic Testing

```bash
# Run basic functionality test
make test_basic

# Run configuration tests
make test_config

# Run all test suites
make test_all

# Run with specific simulator
make test_all SIM=questa
```

### 3. CI/CD Integration

```bash
# Local CI/CD simulation (recommended before commits)
./run_ci_tests.sh

# Quick validation for development
./run_ci_tests.sh --test-suite quick

# Performance benchmarking
./run_ci_tests.sh --test-suite performance --verbose
```

### 4. View Results

```bash
# View waveforms
make waves

# Generate status badges
python3 generate_badges.py

# Check test results
ls results/
```

## Test Cases

### test_filter_basic_functionality
- Configures filter rules from YAML config
- Sends matching and non-matching packets
- Verifies correct filtering behavior
- Checks packet statistics

### test_filter_stress  
- Sends 50 packets rapidly
- Tests performance under load
- Validates no packet loss or corruption

### test_filter_coverage
- Runs multiple test iterations
- Focuses on achieving coverage goals
- Reports detailed coverage metrics

## Configuration

Tests use YAML configuration files:
- `configs/tests/filter_rx_pipeline_basic.yaml` - Test parameters
- `configs/boards/au250.yaml` - Board-specific settings

Example configuration:
```yaml
filter_config:
  num_rules: 2
  rules:
    - rule_id: 0
      src_ip: 0xC0A80101    # 192.168.1.1
      dst_ip: 0xC0A80102    # 192.168.1.2
      protocol: 17          # UDP
      action: "pass"
```

## Environment Components

The testbench uses a layered verification environment:

### Base Components
- `Component`: Abstract base class with lifecycle management
- `Driver`: Base driver for stimulus generation
- `Monitor`: Base monitor for observation
- `Scoreboard`: Transaction checking and comparison
- `Coverage`: Functional coverage collection

### AXI Stream Agent
- `AxiStreamDriver`: Generates AXI Stream transactions
- `AxiStreamMonitor`: Observes AXI Stream interfaces
- `AxiStreamTransaction`: Transaction data structure

### Filter RX Agent  
- `FilterRxDriver`: Filter-specific packet generation
- `FilterRxMonitor`: Filter output monitoring and statistics
- `FilterPacket`: Packet with filter metadata

### Utilities
- `ClockGenerator`: Configurable clock generation
- `ResetManager`: Standardized reset sequences

## Usage Examples

### Custom Test
```python
import cocotb
from tb.env import FilterRxPipelineEnvironment, Config

@cocotb.test()
async def my_custom_test(dut):
    config = Config()
    env = FilterRxPipelineEnvironment(dut, config)
    
    await env.start()
    # Your test logic here
    await env.stop()
```

### Generate Custom Packets
```python
# Create filter-specific packet
packet = env.filter_driver.generate_matching_packet(rule_index=0)
await env.filter_driver.send_filter_packet(packet)

# Send random AXI Stream transaction
await env.input_driver.send_random_transaction(min_size=64, max_size=1500)
```

### Monitor Results
```python
# Wait for packets
success = await env.filter_monitor.wait_for_packets(expected_count=10)

# Get statistics
stats = env.filter_monitor.get_filter_statistics()
print(f"Pass rate: {stats['pass_rate_percent']:.1f}%")
```

## Simulator Support

### Questa
```bash
make test SIM=questa
```

### Xcelium
```bash
make test SIM=xcelium  
```

### VCS
```bash
make test SIM=vcs
```

## Debugging

1. **Enable debug logging**:
   ```python
   import logging
   logging.getLogger("cocotb").setLevel(logging.DEBUG)
   ```

2. **View waveforms**:
   ```bash
   make waves
   ```

3. **Check log files**:
   - `sim_build/` - Compilation logs
   - Test output in terminal

## Coverage

The testbench includes functional coverage for:
- Filter rule usage
- Packet types (matching/non-matching)
- Packet sizes
- Interface signals

View coverage reports in test output or export coverage data:
```python
coverage_data = env.coverage.export_coverage_data()
```

## Test Coverage

This module includes **28 comprehensive test cases** covering all aspects of functionality:

### 🔍 **Basic Functionality** (8 test cases)
- **TC-IPV4-001**: IPv4 packet filtering with rule matching
- **TC-IPV4-002**: IPv4 rule priority and precedence
- **TC-IPV4-003**: Multiple IPv4 rules
- **TC-IPV6-001**: IPv6 packet filtering with rule matching
- **TC-IPV6-002**: IPv6 rule priority and precedence  
- **TC-IPV6-003**: Multiple IPv6 rules
- **TC-MIXED-001**: Mixed IPv4/IPv6 traffic scenarios
- **TC-MIXED-002**: Complex mixed traffic patterns

### ⚙️ **Configuration** (5 test cases)
- **TC-CFG-001**: Rule configuration and validation
- **TC-CFG-002**: Multiple rule configurations
- **TC-CFG-003**: Rule priority and precedence
- **TC-DYN-001**: Dynamic rule updates during traffic
- **TC-DYN-002**: Rule enabling/disabling

### 🚨 **Edge Cases** (5 test cases)
- **TC-EDGE-001**: Malformed packet handling
- **TC-EDGE-002**: Minimum/maximum packet sizes
- **TC-EDGE-003**: Invalid EtherType handling
- **TC-EDGE-004**: Truncated packets
- **TC-EDGE-005**: Back-pressure scenarios

### ⚡ **Performance** (4 test cases)
- **TC-PERF-001**: Maximum throughput measurement (250MHz target)
- **TC-PERF-002**: Burst traffic handling
- **TC-PERF-003**: Sustained traffic performance
- **TC-PERF-004**: Mixed packet size performance

### 🔌 **Protocol Compliance** (4 test cases)
- **TC-AXI-001**: AXI Stream protocol compliance
- **TC-AXI-002**: Packet boundary handling
- **TC-AXI-003**: User signal pass-through
- **TC-INT-001**: Data integrity verification

### 📈 **Statistics** (2 test cases)
- **TC-STAT-001**: Statistics counter accuracy
- **TC-STAT-002**: Counter overflow testing

## Test Suites

| Command | Description | Test Cases | Duration |
|---------|-------------|------------|----------|
| `make test_basic` | Basic filtering functionality | TC-IPV4-*, TC-IPV6-*, TC-MIXED-* | ~5 min |
| `make test_config` | Configuration tests | TC-CFG-*, TC-DYN-* | ~3 min |
| `make test_edge` | Edge cases and error handling | TC-EDGE-* | ~4 min |
| `make test_performance` | Performance and throughput | TC-PERF-* | ~8 min |
| `make test_protocol` | Protocol compliance | TC-AXI-*, TC-INT-* | ~3 min |
| `make test_stats` | Statistics verification | TC-STAT-* | ~2 min |
| **`make test_all`** | **Complete test suite** | **All 28 test cases** | **~25 min** |

### CI/CD Test Suites

| Command | Description | Use Case |
|---------|-------------|----------|
| `make ci_quick` | Quick validation | Pull request checks |
| `make ci_standard` | Standard test suite | Branch push validation |
| `make ci_full` | Complete regression | Nightly builds |
| `make ci_performance` | Performance benchmarks | Performance tracking |

## 🚀 CI/CD Integration

This project includes comprehensive automated testing with GitHub Actions:

### **Automated Triggers**

| Trigger | Test Suite | Description |
|---------|------------|-------------|
| **Pull Request** | `ci_quick` | Fast validation (basic + config tests) |
| **Push to main/develop** | `ci_standard` | Standard validation (excludes performance) |
| **Nightly Schedule** | `ci_full` | Complete regression testing |
| **Manual Dispatch** | Configurable | On-demand testing with custom parameters |

### **Quality Gates**

- ✅ **100% Test Pass Rate**: All tests must pass
- ✅ **Performance Thresholds**: Throughput ≥200 Gbps, Latency ≤10 cycles
- ✅ **Protocol Compliance**: AXI Stream standard compliance
- ✅ **Statistics Accuracy**: Counter validation and overflow handling

### **Automated Features**

- 🔄 **Auto Status Updates**: Real-time badge updates in README
- 📊 **Performance Tracking**: Historical performance data
- 🚨 **Failure Notifications**: Automatic issue creation on failures
- 📝 **Test Reports**: Comprehensive CI/CD reports with artifacts
- 🔧 **Pre-commit Hooks**: Local validation before commits

### **Supported Simulators**

| Simulator | CI/CD Support | Performance | Notes |
|-----------|---------------|-------------|-------|
| **Verilator** | ✅ Primary | Fast | Default for CI/CD |
| **Questa** | ✅ Full | Medium | Enterprise simulation |
| **Xcelium** | ✅ Full | Medium | Cadence simulator |
| **VCS** | ⚠️ Limited | Fast | Synopsys simulator |

## 🛠️ Local Development Workflow

### **Pre-commit Validation**
```bash
# Quick syntax check
python3 validate_tests.py

# Local CI simulation
./run_ci_tests.sh --test-suite quick

# Comprehensive local testing
./run_ci_tests.sh --clean --verbose
```

### **Development Best Practices**
1. **Run validation** before every commit
2. **Use CI/CD simulation** for comprehensive testing
3. **Check performance impact** for changes affecting data path
4. **Update documentation** for new features or test cases
5. **Monitor CI/CD status** after pushing changes

### **Debugging Failed Tests**
```bash
# Run specific test with verbose output
make test_basic SIM=verilator EXTRA_ARGS="--verbose"

# Generate waveforms for debugging
make test_basic SIM=verilator
make waves

# Check CI/CD logs
./run_ci_tests.sh --test-suite basic --verbose
```

## 📊 Performance Monitoring

### **Target Performance Metrics**

| Metric | Target | Measurement | Status |
|--------|--------|-------------|--------|
| **Throughput** | ≥200 Gbps | 250MHz × 512-bit | 📊 CI Tracked |
| **Latency** | ≤10 cycles | Pipeline depth | 📊 CI Tracked |
| **Packet Rate** | ≥100 Mpps | Min-size packets | 📊 CI Tracked |
| **Efficiency** | ≥90% | Utilization ratio | 📊 CI Tracked |

*Performance results are automatically updated by the CI/CD pipeline*

### **Benchmarking**
```bash
# Run performance benchmarks
make ci_performance

# Generate performance report
python3 generate_badges.py

# View historical performance data
cat results/benchmark.json
```

## 🔍 Troubleshooting

### **Common Issues**

1. **Environment Setup Failures**
   ```bash
   # Reset environment
   ./setup_test_env.sh --force
   
   # Check dependencies
   pip install -r requirements.txt
   ```

2. **Simulator Issues**
   ```bash
   # Check simulator installation
   which verilator
   verilator --version
   
   # Try different simulator
   make test_basic SIM=questa
   ```

3. **CI/CD Pipeline Failures**
   ```bash
   # Reproduce locally
   ./run_ci_tests.sh --test-suite standard
   
   # Check specific test
   make test_basic COCOTB_LOG_LEVEL=DEBUG
   ```

### **Getting Help**

- 📖 **Documentation**: [TESTPLAN.md](TESTPLAN.md), [TESTCASES.md](TESTCASES.md)
- 🐛 **Issues**: Use GitHub issues with CI/CD tag
- 💬 **Support**: Tag maintainers in pull requests

## 📚 Documentation

- [**TESTPLAN.md**](TESTPLAN.md) - Master test plan and requirements
- [**TESTCASES.md**](TESTCASES.md) - Detailed test case specifications  
- [**IMPLEMENTATION_SUMMARY.md**](IMPLEMENTATION_SUMMARY.md) - Complete implementation details
- [**utils/**](utils/) - Test utility API documentation

## 🤝 Contributing

### **Development Process**
1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run local validation**: `./run_ci_tests.sh`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request** with CI/CD validation

### **Pull Request Requirements**
- ✅ All CI/CD checks must pass
- ✅ Performance regressions must be justified
- ✅ New features must include tests
- ✅ Documentation must be updated

---

**🎯 Project Status**: ✅ **COMPLETE IMPLEMENTATION**  
**🚀 CI/CD Status**: ✅ **FULLY AUTOMATED**  
**📊 Test Coverage**: ✅ **28/28 TEST CASES**  
**⚡ Performance**: 📊 **Continuously Monitored**

*Last Updated: Auto-updated by CI/CD pipeline*
