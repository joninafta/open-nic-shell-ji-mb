# Filter RX Pipeline Testbench

This directory contains the Cocotb-based testbench for the `filter_rx_pipeline` module, part of the OpenNIC Shell verification environment.

## Overview

The `filter_rx_pipeline` module implements packet filtering based on IPv4, IPv6, and port rules. This testbench provides comprehensive verification including:

- Basic functionality testing
- Stress testing with high packet rates  
- Coverage-driven verification
- Filter rule configuration and validation
- AXI Stream interface compliance

## Structure

```
tb/tests/filter_rx_pipeline/
├── Makefile                    # Build and run targets
├── README.md                   # This file
├── tb_filter_rx_pipeline.sv    # SystemVerilog testbench wrapper
└── test_filter_basic.py        # Python test cases
```

## Dependencies

- **Cocotb**: Python-based verification framework
- **PyYAML**: For configuration file parsing
- **Simulator**: Questa, Xcelium, or VCS

## Quick Start

1. **Set up environment**:
   ```bash
   cd tb/tests/filter_rx_pipeline
   export PROJECT_ROOT=$(pwd)/../../../..
   ```

2. **Run basic test**:
   ```bash
   make test
   ```

3. **Run all tests**:
   ```bash
   make test_all
   ```

4. **View waveforms**:
   ```bash
   make waves
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

## Contributing

When adding new tests:
1. Follow the existing naming convention
2. Add test documentation  
3. Update configuration files if needed
4. Ensure tests clean up properly
5. Add coverage points for new functionality

## Troubleshooting

**Common Issues:**

1. **Import errors**: Check `PYTHONPATH` includes `tb/` directory
2. **Config not found**: Verify `PROJECT_ROOT` environment variable
3. **Simulation errors**: Check file lists and include paths
4. **Clock issues**: Ensure proper clock setup in testbench

**Debug Steps:**
1. Run with verbose logging
2. Check simulator compilation logs
3. Verify DUT instantiation in SystemVerilog wrapper
4. Test with minimal configuration first
