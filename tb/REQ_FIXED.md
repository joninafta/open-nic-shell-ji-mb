# Cocotb-Based Unit‑Level Verification Environment for OpenNIC Shell

## 1. Goals & Guiding Principles

* **Generic & Re‑usable**: One code base should verify any synthesizable RTL block by plugging in a file‑list and minimal configuration.
* **Clear Separation of Concerns**: Distinct stages for *build* (Verilator elaboration) and *run* (Python + cocotb tests).
* **Layered OOP Testbench**: Driver, Monitor, Scoreboard, Coverage collector, and Environment classes, mirroring best practices from UVM but written in Python.
* **Deterministic & Repeatable**: Every run must be 100% reproducible from a clean clone.
* **Developer Ergonomics**: Tab‑completion on CLI scripts, rich logging, and zero clutter in Git (all generated artifacts are ignored).
* **OpenNIC Shell Focused**: Designed specifically for testing OpenNIC shell components like QDMA subsystem, CMAC subsystem, packet adapters, and system configuration modules.
* **Multi‑Board Support**: Support for multiple FPGA boards (AU200, AU250, AU280, AU50, AU55C, AU55N, AU45N) with board‑specific configurations.

---

## 2. Repository Layout

```
<repo_root>/
│  README.md
│  .gitignore
│  pyproject.toml          # if packaging TB utilities
│
├─ src/                    # RTL sources (SystemVerilog design files)
│   ├─ open_nic_shell.sv
│   ├─ box_250mhz/
│   ├─ box_322mhz/
│   ├─ cmac_subsystem/
│   ├─ packet_adapter/
│   ├─ qdma_subsystem/
│   ├─ system_config/
│   ├─ utility/
│   └─ zynq_usplus_ps/
│
├─ tb/                     # Testbench code
│   ├─ env/                # Core verification components
│   │   ├─ base/           # Abstract base classes common to all agents
│   │   │   ├─ driver.py
│   │   │   ├─ monitor.py
│   │   │   ├─ scoreboard.py
│   │   │   ├─ coverage.py
│   │   │   └─ config.py   # Dataclass‑style configuration objects
│   │   ├─ agents/         # One folder per interface‑specific agent
│   │   │   ├─ axi_lite/
│   │   │   │   ├─ driver.py
│   │   │   │   ├─ monitor.py
│   │   │   │   └─ __init__.py
│   │   │   ├─ axi_stream/
│   │   │   │   ├─ driver.py
│   │   │   │   ├─ monitor.py
│   │   │   │   └─ __init__.py
│   │   │   ├─ qdma/
│   │   │   │   ├─ driver.py
│   │   │   │   ├─ monitor.py
│   │   │   │   └─ __init__.py
│   │   │   └─ cmac/
│   │   │       ├─ driver.py
│   │   │       ├─ monitor.py
│   │   │       └─ __init__.py
│   │   ├─ env.py          # Composes agents + scoreboards
│   │   └─ __init__.py
│   ├─ tests/              # Block‑specific test cases (thin wrappers)
│   │   ├─ qdma_subsystem/
│   │   │   ├─ test_qdma_basic.py
│   │   │   ├─ test_qdma_multiqueue.py
│   │   │   └─ sequences.py
│   │   ├─ cmac_subsystem/
│   │   │   ├─ test_cmac_basic.py
│   │   │   └─ sequences.py
│   │   ├─ packet_adapter/
│   │   │   ├─ test_adapter_basic.py
│   │   │   └─ sequences.py
│   │   ├─ system_config/
│   │   │   ├─ test_config_basic.py
│   │   │   └─ sequences.py
│   │   └─ utility/
│   │       ├─ test_axi_stream_fifo.py
│   │       ├─ test_reset_gen.py
│   │       └─ sequences.py
│   ├─ models/             # Reference models and checkers
│   │   ├─ packet_models.py
│   │   ├─ axi_models.py
│   │   └─ qdma_models.py
│   └─ utils/              # Timing helpers, randomization, etc.
│       ├─ clock_gen.py
│       ├─ reset_utils.py
│       └─ random_utils.py
│
├─ script/                 # Front‑end user commands & build utilities
│   ├─ build.py            # Elaborate & compile with Verilator
│   ├─ run.py              # Launch compiled sim + cocotb
│   ├─ __init__.py
│   └─ tb/                 # Legacy scripts (compatibility)
│       ├─ run.do
│       └─ run.sh
│
├─ filelists/              # One *.f per design block or variant
│   ├─ qdma_subsystem.f
│   ├─ cmac_subsystem.f
│   ├─ packet_adapter.f
│   ├─ system_config.f
│   ├─ utility_modules.f
│   └─ open_nic_shell.f
│
├─ configs/                # Board and test configurations
│   ├─ boards/
│   │   ├─ au200.yaml
│   │   ├─ au250.yaml
│   │   ├─ au280.yaml
│   │   ├─ au50.yaml
│   │   ├─ au55c.yaml
│   │   ├─ au55n.yaml
│   │   └─ au45n.yaml
│   └─ tests/
│       ├─ qdma_config.yaml
│       ├─ cmac_config.yaml
│       └─ default.yaml
│
├─ build/                  # **IGNORED** – Verilator obj_dir & binaries
├─ sim/                    # **IGNORED** – Per‑run logs, vcd, coverage
├─ constr/                 # Constraint files (for reference)
└─ docs/                   # Architecture docs like this file
```

### Rationale

* `tb/env` holds technology‑agnostic verification IP, reusable across blocks.
* `tb/tests/<block>` encloses tiny, focused tests that import the common env.
* `script` exposes a uniform UX; everything else is an implementation detail.
* `src/` contains the actual OpenNIC shell RTL sources organized by subsystem.
* `configs/` separates board‑specific parameters from test‑specific configurations.
* `filelists/` organized by major subsystems for efficient compilation.

---

## 3. Verification Class Hierarchy

```
+----------------------+         +-------------------+
| CocotbTest           |---------| Environment (Env) |
|  (per‑test module)   |  uses   +-------------------+
|                      |                 | aggregates
+----------------------+                 v
                                        +-------------------+
                                        | Agents[...]       |
                                        +-------------------+
                                                | has
+-----------+   +-----------+   +-----------+   +-----------+
| Driver    |   | Monitor   |   | Scoreboard|   | Coverage  |
+-----------+   +-----------+   +-----------+   +-----------+
```

* **Config**: Frozen dataclass passed top‑down; supports YAML/JSON load with board‑specific parameters.
* **Agent**: Bundles one Driver + Monitor for a given interface (AXI‑Lite, AXI‑Stream, QDMA, CMAC).
* **Environment**: Instantiated inside every test; builds agents based on config and DUT type.
* **Scoreboard**: Reference model comparison; plugs into monitors via queues.
* **Coverage**: Optional, centralized functional coverage sampling with OpenNIC‑specific metrics.

All classes inherit from a thin `Component` base that offers
`start()`, `stop()`, `log`, and `raise_test_failure()` utility methods.

### OpenNIC‑Specific Agents

* **QDMAAgent**: Handles QDMA H2C/C2H data streams, completion queues, and bypass modes
* **CMACAgent**: Manages CMAC TX/RX interfaces with ethernet frame validation
* **AXILiteAgent**: Generic AXI‑Lite register interface agent for configuration
* **AXIStreamAgent**: Generic AXI‑Stream interface with packet‑level awareness
* **PacketAdapterAgent**: Specialized for packet adapter RX/TX paths with metadata handling

---

## 4. Build & Run Flow

### 4.1 Build Stage (`script/build.py`)

| Step | Action                                                               |
| ---- | -------------------------------------------------------------------- |
| 1    | Parse CLI (`--filelist`, `--top TOP_MODULE`, `--board`, `--outdir`) |
| 2    | Load board‑specific configuration from `configs/boards/<board>.yaml` |
| 3    | Resolve relative paths, create dedicated `build/<hash>/…` folder     |
| 4    | Call Verilator with best‑practice flags (lint off, coverage on, VPI) |
| 5    | Handle SystemVerilog defines for board selection (`__au280__`, etc.) |
| 6    | Generate executable `simv`, plus waveform & coverage knobs           |
| 7    | Emit compile database (`compile_commands.json`) for IDEs             |

**Simulator Requirements**: 
- **Primary Simulator**: Verilator is the required and officially supported simulator for this verification environment
- **Not Supported**: Icarus Verilog is explicitly not supported due to limited SystemVerilog support and incompatibility with Cocotb VPI requirements
- **Commercial Simulators**: For advanced debugging, Questa, Xcelium, and VCS are supported as secondary options

**Board Support**: Automatically applies correct defines and parameters based on `--board` selection:
- AU200, AU250, AU280: Dual QSFP+ configuration
- AU50, AU55C, AU55N: HBM memory support  
- AU45N: Zynq UltraScale+ PS integration

**Tab‑Completion**: Implement with *python‑argcomplete*; user runs `eval "$(register-python-argcomplete build.py)"` once in their shell profile.

### 4.2 Run Stage (`script/run.py`)

| Step | Action                                                                |
| ---- | --------------------------------------------------------------------- |
| 1    | Parse CLI (`--test qdma.test_qdma_basic`, `--seed`, `--waves`, `--board`) |
| 2    | Load test‑specific configuration from `configs/tests/<test>.yaml`     |
| 3    | Export required environment: `COCOTB_TESTMODULE`, `COCOTB_SEED`, etc. |
| 4    | Set board‑specific parameters and test constraints                    |
| 5    | Spawn compiled `simv`; propagate exit status back to caller           |
| 6    | Collect artifacts into `sim/<timestamp>/` (logs, **VCD**, coverage)   |

**Enhanced Features**:
- Automatic test discovery based on module structure
- Board‑aware parameter passing to testbench
- Integration with existing `script/tb/run.sh` for backwards compatibility
- Parallel test execution support for regression testing

Both scripts return non‑zero on failure so they chain nicely in CI pipelines.

---

## 5. OpenNIC‑Specific Testing Requirements

### Interface Protocols & Standards

* **QDMA Interfaces**: Support for Xilinx QDMA IP with H2C/C2H streaming, completion queues, and bypass modes
* **AXI‑Stream**: Packet‑aware with proper `tkeep`, `tlast`, and user signal handling
* **AXI‑Lite**: Register interface testing with proper address mapping and error responses
* **CMAC**: 100G Ethernet MAC interfaces with frame validation and flow control
* **Board‑Specific GPIO**: QSFP management, HBM temperature monitoring, satellite GPIO

### Multi‑Board Considerations

* **Clock Domains**: Different boards have varying clock frequencies (250MHz, 322MHz, 100MHz reference)
* **Memory Interfaces**: HBM support on AU50/AU55 series, PCIe configurations vary by board
* **QSFP Configuration**: AU200/AU250/AU280 have dual QSFP+, others may differ
* **PS Integration**: AU45N includes Zynq UltraScale+ PS requiring special handling

### Test Coverage Requirements

* **Functional Coverage**: 
  - Packet size distributions (64B to 9KB)
  - Queue utilization patterns
  - Error injection and recovery
  - Multi‑function scenarios
  
* **Protocol Compliance**:
  - AXI4‑Stream protocol checker
  - Ethernet frame format validation
  - PCIe TLP structure verification
  - Register access patterns

* **Performance Metrics**:
  - Throughput measurement at line rate
  - Latency characterization
  - Queue depth utilization
  - Error rate monitoring

---

## 6. Simulator Requirements & Dependencies

### Required Simulator: Verilator

This verification environment is specifically designed for **Verilator** as the primary simulation engine:

* **Verilator 4.106+**: Required for proper SystemVerilog support and Cocotb VPI integration
* **Installation**: `sudo apt install verilator` or build from source for latest features
* **Features Used**: 
  - SystemVerilog elaboration with proper interface support
  - VPI (Verilog Procedural Interface) for Cocotb integration
  - Coverage collection (line and toggle coverage)
  - Waveform generation (VCD/FST formats)

### Explicitly NOT Supported

* **Icarus Verilog**: Not supported due to:
  - Limited SystemVerilog interface support
  - Incompatible VPI implementation with Cocotb requirements
  - Missing essential features for complex OpenNIC designs
  - Poor performance with large hierarchical designs

### Secondary Simulators (Advanced Users)

For advanced debugging and commercial EDA flows, the following are supported:
* **Questa Sim**: Professional simulator with advanced debugging
* **Xcelium**: Cadence simulator for enterprise environments  
* **VCS**: Synopsys simulator for high-performance simulation

### Python Dependencies

```bash
# Required Python packages
pip install cocotb cocotb-bus pyyaml dataclasses

# Optional but recommended
pip install pytest pytest-html coverage
```

---

## 7. Continuous Integration & Regression Testing

### GitHub Actions Workflow

* **Multi‑Board Testing**: Matrix over all supported boards (AU200, AU250, AU280, AU50, AU55C, AU55N, AU45N)
* **Cached Dependencies**: Verilator installation (required), Python packages, and board‑specific IP cores
* **Parallel Execution**: Run subsystem tests in parallel for faster feedback
* **Artifact Collection**: 
  - JUnit XML test results
  - Coverage reports (line, branch, functional)
  - VCD waveforms for failed tests
  - Build logs and synthesis reports

### Regression Test Suite Structure

```bash
# Full regression across all boards and tests
./script/run_regression.py --all-boards --all-tests

# Board-specific regression
./script/run_regression.py --board au280 --subsystem qdma_subsystem

# Smoke test for quick validation
./script/run_regression.py --smoke-test --boards au280,au250
```

### Integration with Existing Vivado Flow

* **Compatibility**: Cocotb tests complement existing Vivado simulation in `script/tb/`
* **Shared Resources**: Reuse existing constraint files from `constr/` for board awareness
* **IP Integration**: Leverage Vivado IP definitions from `src/*/vivado_ip/` folders

---

## 8. Local-CI Validation Alignment

### Problem Statement

A critical challenge in verification environments is ensuring **validation parity** between local development and CI environments. Discrepancies can lead to:
- Tests passing locally but failing in CI due to different validation depths
- False confidence in code quality during development
- Delayed detection of import errors and missing dependencies
- Reduced developer productivity due to CI-only failures

### Root Cause Analysis: Validation Depth Mismatch

The investigation of Filter RX Pipeline test failures revealed fundamental differences between local and CI validation approaches:

**Local Validation (Syntax-Only)**:
```bash
# setup_test_env.sh runs syntax validation only
python validate_tests.py --run-syntax-check
```
- Performs AST parsing and syntax validation
- Detects syntax errors, indentation issues
- **Does NOT** perform actual imports or runtime validation
- **Does NOT** detect missing functions or broken import paths

**CI Validation (Full Runtime)**:
```bash
# CI runs full runtime import validation
python validate_tests.py  # no flags = full validation
```
- Performs actual module imports using `importlib.util.spec_from_file_location()`
- Executes module initialization code
- **DOES** detect missing functions, broken imports, path resolution issues
- **DOES** catch runtime import dependencies

### Recommended Solutions

#### 1. Align Local Validation with CI

**Immediate Fix**: Modify local validation scripts to match CI behavior:

```bash
# In setup_test_env.sh - replace syntax-only with full validation
python validate_tests.py  # Remove --run-syntax-check flag
```

**Benefits**:
- Immediate parity between local and CI validation
- Earlier detection of import issues during development
- Reduced CI failure rate due to preventable errors

#### 2. Implement Dual-Stage Validation

**Enhanced Approach**: Provide both fast and comprehensive validation options:

```bash
# Fast feedback for rapid development iteration
python validate_tests.py --syntax-only

# Comprehensive validation matching CI (run before commits)
python validate_tests.py --full-validation
```

**Implementation Strategy**:
- Default local behavior should match CI (full validation)
- Provide explicit `--syntax-only` flag for rapid iteration
- Document when each mode should be used

#### 3. Runtime Import Diagnostic Tools

**Create CI-Equivalent Local Tools**: Develop scripts that replicate CI validation methodology:

```python
# Example: test_runtime_imports.py
import importlib.util
import sys
import os

def validate_runtime_imports(test_file_path):
    """Perform CI-style runtime import validation locally"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "Import successful"
    except Exception as e:
        return False, f"Import failed: {e}"
```

**Usage**:
- Run diagnostic tools during development
- Catch import issues before committing
- Validate dependency resolution locally

#### 4. Path Resolution Best Practices

**Consistent Import Strategy**: Establish patterns that work reliably across environments:

```python
# Robust path resolution for test imports
import os
import sys

# Add project root to Python path
current_test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_test_dir, '../../..')
sys.path.insert(0, project_root)

# Now imports work consistently in both local and CI
import tb.tests.common_utils as common_utils
```

**Avoid Problematic Patterns**:
```python
# AVOID: Relative path strings that vary by execution context
sys.path.append('../../../../tb')  # Fragile

# PREFER: Computed absolute paths from file location
project_root = os.path.abspath(os.path.join(__file__, '../../..'))
sys.path.insert(0, project_root)
```

### Implementation Guidelines for Future Projects

#### 1. Design Validation Strategy Early

**During Project Setup**:
- Define validation requirements for both local and CI environments
- Establish what level of validation is needed (syntax vs. runtime vs. execution)
- Document the rationale for validation depth choices

#### 2. Environment Parity Checklist

**Before Implementing Validation Scripts**:
- [ ] Local validation depth matches CI validation depth
- [ ] Import path resolution strategies are environment-agnostic
- [ ] Missing dependency detection works in both environments
- [ ] Validation failure modes are consistent (same errors, same exit codes)

#### 3. Testing Validation Tools

**Validate the Validators**:
- Test validation scripts against known-good and known-bad code
- Verify that local validation catches the same issues as CI
- Include validation tool testing in regression suites

#### 4. Developer Workflow Integration

**Make Comprehensive Validation Easy**:
```bash
# Pre-commit hook example
#!/bin/bash
echo "Running comprehensive validation (matching CI)..."
python validate_tests.py --full-validation
if [ $? -ne 0 ]; then
    echo "Validation failed - fix errors before committing"
    exit 1
fi
```

#### 5. Documentation Requirements

**For Every Validation Script**:
- Document the validation depth and methodology
- Explain differences between validation modes (if multiple exist)
- Provide examples of what each validation level catches
- Include troubleshooting guides for common validation failures

### Lessons Learned from Filter RX Pipeline Investigation

1. **Syntax validation alone is insufficient** for complex projects with runtime dependencies
2. **Import path resolution is environment-sensitive** and requires careful absolute path handling
3. **Missing function detection requires actual import execution**, not just syntax parsing
4. **CI validation methodology should be replicable locally** for effective development workflows
5. **Validation discrepancies lead to technical debt** in the form of CI-only debugging cycles

### Future Enhancements

#### Automated Validation Alignment

**Tool Development Opportunities**:
- Automated validation parity checker
- CI environment simulator for local testing
- Import dependency analyzer
- Path resolution validator

#### Integration with Development Tools

**IDE and Editor Integration**:
- VS Code extensions for validation feedback
- Pre-commit hooks with validation
- Real-time import validation during editing

---

## 9. Extending to New OpenNIC Subsystems

1. **Identify the subsystem**: Choose from `qdma_subsystem`, `cmac_subsystem`, `packet_adapter`, `system_config`, or `utility` modules.
2. **Create filelist**: Add a new `filelists/<subsystem>.f` file listing all RTL sources for that subsystem.
3. **Configure for board**: Ensure proper SystemVerilog defines are included for target board (`__au280__`, `__au250__`, etc.).
4. **Create test directory**: Set up `tb/tests/<subsystem>/` with appropriate test cases.
5. **Define board configurations**: Update `configs/boards/<board>.yaml` if subsystem has board‑specific parameters.

### Example: Adding QDMA Subsystem Tests

```bash
# Create filelist for QDMA subsystem
echo "src/qdma_subsystem/qdma_subsystem.sv" > filelists/qdma_subsystem.f
echo "src/qdma_subsystem/qdma_subsystem_*.sv" >> filelists/qdma_subsystem.f
echo "src/utility/axi_*.sv" >> filelists/qdma_subsystem.f

# Build for AU280 board
python script/build.py --filelist filelists/qdma_subsystem.f --top qdma_subsystem --board au280

# Run basic QDMA test
python script/run.py --test qdma_subsystem.test_qdma_basic --board au280 --waves
```

### OpenNIC‑Specific Test Categories

* **QDMA Tests**: H2C/C2H data transfer, queue management, completion handling, bypass modes
* **CMAC Tests**: Ethernet frame TX/RX, flow control, error injection, loopback
* **Packet Adapter Tests**: RX/TX path validation, metadata handling, packet filtering
* **System Config Tests**: Register access, board‑specific GPIO, reset sequences, clock management
* **Utility Tests**: AXI‑Stream FIFO, reset generators, CRC calculations, arbiters

---

## 10. Enhanced .gitignore

```gitignore
# Build & simulation artifacts
/build/
/sim/
**/obj_dir/
*.vcd
*.fst
*.vpd
*.shm/
*.trn
*.dsn
coverage.dat
*.gcda
*.gcno

# Python & Cocotb clutter
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
cocotb_build/
results.xml
sim_build/
.coverage
htmlcov/

# Editors & IDEs
.vscode/
.idea/
*.swp
*~
.DS_Store

# Vivado artifacts (enhanced from existing .gitignore)
vivado*.jou
vivado*.log
vivado*.str
.Xil/
.comp/
.sim/
*.bit
*.ltx
*.rpt
*.dcp

# Temporary files
*.tmp
*.temp
*.lock
.#*
\#*#
```

---

## 11. Project‑Specific Considerations

### Integration with OpenNIC Architecture

* **Shell‑Plugin Interface**: Tests must validate the interface between shell (`src/`) and plugins (`plugin/`)
* **Box Domains**: Separate 250MHz and 322MHz clock domains require careful synchronization testing
* **Multi‑Queue Architecture**: QDMA supports multiple physical functions and queues requiring sophisticated test scenarios
* **Board Variant Testing**: Each board has unique constraints and capabilities requiring targeted test coverage

### Leveraging Existing Infrastructure

* **Reuse Constraint Files**: Utilize existing timing and pin constraints from `constr/` for realistic testing
* **Board Settings Integration**: Leverage `script/board_settings/` for board‑specific parameters
* **IP Core Compatibility**: Ensure compatibility with existing Vivado IP cores in `src/*/vivado_ip/`
* **Build System Integration**: Complement rather than replace the existing Vivado‑based build flow

### Migration Strategy

1. **Parallel Development**: Develop cocotb infrastructure alongside existing Vivado simulation
2. **Gradual Adoption**: Start with utility module testing, expand to full subsystems
3. **Validation Bridge**: Cross‑validate results between cocotb and existing test infrastructure
4. **Training & Documentation**: Provide comprehensive guides for team adoption

---

## 12. Success Metrics & Validation

### Quantitative Goals

* **Coverage**: Achieve >90% line coverage across all major subsystems
* **Performance**: Test execution <5 minutes for basic regression, <30 minutes for full suite
* **Reliability**: >99% test pass rate on supported boards with deterministic results
* **Efficiency**: 50%+ reduction in test development time vs. traditional methods

### Qualitative Objectives

* **Developer Experience**: Intuitive CLI, rich logging, easy debugging with waveforms
* **Maintainability**: Clear separation of concerns, reusable components, minimal duplication
* **Extensibility**: Easy addition of new boards, interfaces, and test scenarios
* **Integration**: Seamless workflow with existing tools and processes

---

*End of enhanced specification for OpenNIC Shell Cocotb‑based verification environment.*

**Document Version**: 1.2  
**Last Updated**: May 29, 2025  
**Status**: Ready for implementation
