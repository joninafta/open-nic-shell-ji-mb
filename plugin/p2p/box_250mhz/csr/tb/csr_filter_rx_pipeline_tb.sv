// *************************************************************************
//
// CSR Filter RX Pipeline Testbench
// Simple testbench to verify AXI-Lite register interface functionality
//
// Tests:
// 1. Write and readback of all configuration registers
// 2. Read-only status registers
// 3. Address boundary checking
//
// *************************************************************************

`timescale 1ns / 1ps

import cfg_reg_pkg::*;

module csr_filter_rx_pipeline_tb();

    // Parameters
    parameter ADDR_WIDTH = 12;
    parameter REG_PREFIX = 16'hB000;
    parameter CLK_PERIOD = 4; // 250MHz

    // Clock and reset
    logic                    aclk;
    logic                    aresetn;

    // AXI-Lite interface signals
    logic                    s_axil_awvalid;
    logic [ADDR_WIDTH-1:0]   s_axil_awaddr;
    logic                    s_axil_awready;
    logic                    s_axil_wvalid;
    logic [31:0]             s_axil_wdata;
    logic                    s_axil_wready;
    logic                    s_axil_bvalid;
    logic [1:0]              s_axil_bresp;
    logic                    s_axil_bready;
    logic                    s_axil_arvalid;
    logic [ADDR_WIDTH-1:0]   s_axil_araddr;
    logic                    s_axil_arready;
    logic                    s_axil_rvalid;
    logic [31:0]             s_axil_rdata;
    logic [1:0]              s_axil_rresp;
    logic                    s_axil_rready;

    // Configuration register output
    cfg_reg_t                cfg_reg;

    // Test variables
    logic [31:0] test_data;
    logic [31:0] read_data;
    integer test_count = 0;
    integer error_count = 0;

    // DUT instantiation
    csr_filter_rx_pipeline #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .REG_PREFIX(REG_PREFIX)
    ) dut (
        .s_axil_awvalid(s_axil_awvalid),
        .s_axil_awaddr(s_axil_awaddr),
        .s_axil_awready(s_axil_awready),
        .s_axil_wvalid(s_axil_wvalid),
        .s_axil_wdata(s_axil_wdata),
        .s_axil_wready(s_axil_wready),
        .s_axil_bvalid(s_axil_bvalid),
        .s_axil_bresp(s_axil_bresp),
        .s_axil_bready(s_axil_bready),
        .s_axil_arvalid(s_axil_arvalid),
        .s_axil_araddr(s_axil_araddr),
        .s_axil_arready(s_axil_arready),
        .s_axil_rvalid(s_axil_rvalid),
        .s_axil_rdata(s_axil_rdata),
        .s_axil_rresp(s_axil_rresp),
        .s_axil_rready(s_axil_rready),
        .cfg_reg(cfg_reg),
        .aclk(aclk),
        .aresetn(aresetn)
    );

    // Clock generation
    always #(CLK_PERIOD/2) aclk = ~aclk;

    // Initialize signals
    initial begin
        aclk = 0;
        aresetn = 0;
        
        // Initialize AXI-Lite signals
        s_axil_awvalid = 0;
        s_axil_awaddr = 0;
        s_axil_wvalid = 0;
        s_axil_wdata = 0;
        s_axil_bready = 0;
        s_axil_arvalid = 0;
        s_axil_araddr = 0;
        s_axil_rready = 0;

        // Reset sequence
        repeat(10) @(posedge aclk);
        aresetn = 1;
        repeat(5) @(posedge aclk);

        $display("=== CSR Filter RX Pipeline Testbench Started ===");
        
        // Run tests
        test_reset_values();
        test_rule0_registers();
        test_rule1_registers();
        test_status_registers();
        test_invalid_addresses();
        
        // Test summary
        $display("\n=== Test Summary ===");
        $display("Total tests: %0d", test_count);
        $display("Errors: %0d", error_count);
        
        if (error_count == 0) begin
            $display("*** ALL TESTS PASSED ***");
        end else begin
            $display("*** %0d TESTS FAILED ***", error_count);
        end
        
        $finish;
    end

    //========================================================================
    // Test Tasks
    //========================================================================

    // Test that all registers reset to 0
    task test_reset_values();
        $display("\n--- Testing Reset Values ---");
        
        // Check that cfg_reg output is all zeros after reset
        if (cfg_reg.filter_rules[0].ipv4_addr !== 32'h0) begin
            $error("Rule0 IPv4 addr not reset to 0: 0x%h", cfg_reg.filter_rules[0].ipv4_addr);
            error_count++;
        end
        
        if (cfg_reg.filter_rules[0].ipv6_addr !== 128'h0) begin
            $error("Rule0 IPv6 addr not reset to 0: 0x%h", cfg_reg.filter_rules[0].ipv6_addr);
            error_count++;
        end
        
        if (cfg_reg.filter_rules[0].port !== 32'h0) begin
            $error("Rule0 port not reset to 0: 0x%h", cfg_reg.filter_rules[0].port);
            error_count++;
        end

        test_count++;
        $display("Reset values test completed");
    endtask

    // Test Rule 0 register writes and reads
    task test_rule0_registers();
        $display("\n--- Testing Rule 0 Registers ---");
        
        // Test IPv4 address
        test_data = 32'hC0A80101; // 192.168.1.1
        write_register(RULE0_IPV4_OFFSET, test_data);
        read_register(RULE0_IPV4_OFFSET, read_data);
        check_value("Rule0 IPv4", test_data, read_data);
        
        // Test IPv6 address (4 parts)
        test_data = 32'h20010DB8; // First 32 bits
        write_register(RULE0_IPV6_0_OFFSET, test_data);
        read_register(RULE0_IPV6_0_OFFSET, read_data);
        check_value("Rule0 IPv6[31:0]", test_data, read_data);
        
        test_data = 32'h00000000; // Second 32 bits
        write_register(RULE0_IPV6_1_OFFSET, test_data);
        read_register(RULE0_IPV6_1_OFFSET, read_data);
        check_value("Rule0 IPv6[63:32]", test_data, read_data);
        
        test_data = 32'h00000000; // Third 32 bits
        write_register(RULE0_IPV6_2_OFFSET, test_data);
        read_register(RULE0_IPV6_2_OFFSET, read_data);
        check_value("Rule0 IPv6[95:64]", test_data, read_data);
        
        test_data = 32'h00000001; // Fourth 32 bits
        write_register(RULE0_IPV6_3_OFFSET, test_data);
        read_register(RULE0_IPV6_3_OFFSET, read_data);
        check_value("Rule0 IPv6[127:96]", test_data, read_data);
        
        // Test port
        test_data = 32'h00001F90; // Port 8080
        write_register(RULE0_PORT_OFFSET, test_data);
        read_register(RULE0_PORT_OFFSET, read_data);
        check_value("Rule0 Port", test_data, read_data);
        
        $display("Rule 0 register tests completed");
    endtask

    // Test Rule 1 register writes and reads
    task test_rule1_registers();
        $display("\n--- Testing Rule 1 Registers ---");
        
        // Test IPv4 address
        test_data = 32'hAC100002; // 172.16.0.2
        write_register(RULE1_IPV4_OFFSET, test_data);
        read_register(RULE1_IPV4_OFFSET, read_data);
        check_value("Rule1 IPv4", test_data, read_data);
        
        // Test IPv6 address (4 parts)
        test_data = 32'h20010DB8; // First 32 bits
        write_register(RULE1_IPV6_0_OFFSET, test_data);
        read_register(RULE1_IPV6_0_OFFSET, read_data);
        check_value("Rule1 IPv6[31:0]", test_data, read_data);
        
        test_data = 32'h00000003; // Second 32 bits
        write_register(RULE1_IPV6_1_OFFSET, test_data);
        read_register(RULE1_IPV6_1_OFFSET, read_data);
        check_value("Rule1 IPv6[63:32]", test_data, read_data);
        
        test_data = 32'h00000000; // Third 32 bits
        write_register(RULE1_IPV6_2_OFFSET, test_data);
        read_register(RULE1_IPV6_2_OFFSET, read_data);
        check_value("Rule1 IPv6[95:64]", test_data, read_data);
        
        test_data = 32'h00000200; // Fourth 32 bits
        write_register(RULE1_IPV6_3_OFFSET, test_data);
        read_register(RULE1_IPV6_3_OFFSET, read_data);
        check_value("Rule1 IPv6[127:96]", test_data, read_data);
        
        // Test port
        test_data = 32'h00000050; // Port 80
        write_register(RULE1_PORT_OFFSET, test_data);
        read_register(RULE1_PORT_OFFSET, read_data);
        check_value("Rule1 Port", test_data, read_data);
        
        $display("Rule 1 register tests completed");
    endtask

    // Test status registers (read-only)
    task test_status_registers();
        $display("\n--- Testing Status Registers ---");
        
        // Note: Status registers should read the values from the external cfg_reg input
        // Since we don't have a way to set those in this testbench, they should read as 0
        
        read_register(RULE0_HIT_COUNT_OFFSET, read_data);
        check_value("Rule0 Hit Count", 32'h0, read_data);
        
        read_register(RULE1_HIT_COUNT_OFFSET, read_data);
        check_value("Rule1 Hit Count", 32'h0, read_data);
        
        read_register(TOTAL_PKT_COUNT_OFFSET, read_data);
        check_value("Total Packet Count", 32'h0, read_data);
        
        read_register(DROP_PKT_COUNT_OFFSET, read_data);
        check_value("Drop Packet Count", 32'h0, read_data);
        
        $display("Status register tests completed");
    endtask

    // Test invalid address handling
    task test_invalid_addresses();
        $display("\n--- Testing Invalid Address Handling ---");
        
        // Test write to invalid address
        write_register(12'hFFF, 32'hDEADBEEF);
        
        // Test read from invalid address
        read_register(12'hFFF, read_data);
        check_value("Invalid Address Read", 32'h0, read_data);
        
        $display("Invalid address tests completed");
    endtask

    //========================================================================
    // AXI-Lite Protocol Tasks
    //========================================================================

    // Write to a register
    task write_register(input [ADDR_WIDTH-1:0] addr, input [31:0] data);
        @(posedge aclk);
        
        // Address phase
        s_axil_awvalid = 1;
        s_axil_awaddr = addr;
        s_axil_wvalid = 1;
        s_axil_wdata = data;
        
        // Wait for address ready
        while (!s_axil_awready) @(posedge aclk);
        
        // Wait for write ready
        while (!s_axil_wready) @(posedge aclk);
        
        @(posedge aclk);
        s_axil_awvalid = 0;
        s_axil_wvalid = 0;
        
        // Response phase
        s_axil_bready = 1;
        while (!s_axil_bvalid) @(posedge aclk);
        
        @(posedge aclk);
        s_axil_bready = 0;
        
        $display("Wrote 0x%h to address 0x%h", data, addr);
    endtask

    // Read from a register
    task read_register(input [ADDR_WIDTH-1:0] addr, output [31:0] data);
        @(posedge aclk);
        
        // Address phase
        s_axil_arvalid = 1;
        s_axil_araddr = addr;
        
        // Wait for address ready
        while (!s_axil_arready) @(posedge aclk);
        
        @(posedge aclk);
        s_axil_arvalid = 0;
        
        // Data phase
        s_axil_rready = 1;
        while (!s_axil_rvalid) @(posedge aclk);
        
        data = s_axil_rdata;
        
        @(posedge aclk);
        s_axil_rready = 0;
        
        $display("Read 0x%h from address 0x%h", data, addr);
    endtask

    // Check if two values match
    task check_value(input string name, input [31:0] expected, input [31:0] actual);
        test_count++;
        if (expected !== actual) begin
            $error("%s mismatch: expected 0x%h, got 0x%h", name, expected, actual);
            error_count++;
        end else begin
            $display("%s: PASS (0x%h)", name, actual);
        end
    endtask

endmodule
