# GitHub Actions for Open NIC Shell

This directory contains GitHub Actions workflows for automated testing and validation.

## Workflows

### PR Build and Test (`pr-build-test.yml`)

**Triggers:**
- Pull requests to `main` branch that modify:
  - `plugin/p2p/box_250mhz/filter_rx_pipeline/**`
  - `src/**` 
  - `script/**`
  - The workflow file itself
- Manual dispatch with test type selection

**Jobs:**

1. **build-and-test**: Main CI/CD pipeline
   - Sets up Ubuntu environment with Python 3.10 and Verilator
   - Builds the filter RX pipeline using `build.sh`
   - Runs smoke tests (reset, ipv4_rule_matching, counter_verification)
   - Runs full regression suite (12 tests) for comprehensive validation
   - Collects and uploads test logs as artifacts
   - Fails the build if any tests fail

2. **lint-and-format**: Code quality checks
   - Lints Python code with flake8
   - Checks SystemVerilog syntax with Verilator
   - Ensures code quality standards

3. **security-scan**: Basic security validation
   - Scans for sensitive files and credentials
   - Basic security hygiene checks

**Test Types (Manual Dispatch):**
- `smoke`: Quick smoke tests only
- `regression`: Full regression suite (default)
- `individual`: Single test with verbose output

**Artifacts:**
- Test logs and results (retained for 7 days)
- Build artifacts and simulation outputs

## Usage

The workflow runs automatically on PRs. For manual testing:

1. Go to Actions tab in GitHub
2. Select "Build and Test Filter RX Pipeline"
3. Click "Run workflow"
4. Choose test type and run

## Test Results

The workflow provides:
- ✅ Pass/fail status for each test
- 📊 Test summary with counts and percentages  
- 📁 Downloadable test logs and artifacts
- 🚨 Clear failure reporting with details

## Requirements

- Tests must pass before PR can be merged
- Build must complete successfully
- No critical linting issues
- Security scan must pass

## Local Testing

To run the same tests locally:

```bash
# Build
cd plugin/p2p/box_250mhz/filter_rx_pipeline/scripts
./build.sh

# Run tests
python3 run_tests.py reset              # Smoke test
python3 run_tests.py regression         # Full suite
python3 run_tests.py ipv4_rule_matching -v  # Individual test
```
