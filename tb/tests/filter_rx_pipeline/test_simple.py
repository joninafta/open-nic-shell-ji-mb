import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_build_system(dut):
    """Verify build system works."""
    dut._log.info("✅ Build system test PASSED - Simulation running successfully!")
    await Timer(10, units="ns")
