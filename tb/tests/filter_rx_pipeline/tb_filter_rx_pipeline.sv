/**
 * SystemVerilog testbench wrapper for filter_rx_pipeline
 * This provides the DUT instantiation for Cocotb testing
 */

`timescale 1ns / 1ps

import cfg_reg_pkg::*;

module tb_filter_rx_pipeline;

    // Clock and reset  
    logic aclk;
    logic aresetn;
    
    // AXI Stream input interface (using actual signal names)
    logic        s_axis_tvalid;
    logic        s_axis_tready;
    logic [511:0] s_axis_tdata;
    logic [63:0]  s_axis_tkeep;
    logic        s_axis_tlast;
    logic [47:0]  s_axis_tuser;
    
    // AXI Stream output interface (using actual signal names)
    logic        m_axis_tvalid;
    logic        m_axis_tready;
    logic [511:0] m_axis_tdata;
    logic [63:0]  m_axis_tkeep;
    logic        m_axis_tlast;
    logic [47:0]  m_axis_tuser;
    
    // Configuration and status interfaces
    cfg_reg_t    cfg_reg;
    status_reg_t status_reg;
    
    // Device Under Test
    filter_rx_pipeline #(
        .NUM_RULES(2)
    ) dut (
        // Clock and reset
        .aclk(aclk),
        .aresetn(aresetn),
        
        // Slave AXI Stream Interface (from adapter)
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tkeep(s_axis_tkeep),
        .s_axis_tlast(s_axis_tlast),
        .s_axis_tuser(s_axis_tuser),
        
        // Master AXI Stream Interface (to QDMA)
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tkeep(m_axis_tkeep),
        .m_axis_tlast(m_axis_tlast),
        .m_axis_tuser(m_axis_tuser),
        
        // Configuration register input
        .cfg_reg(cfg_reg),
        
        // Configuration register output (status)
        .status_reg(status_reg)
    );
    
    // Initialize configuration registers
    initial begin
        cfg_reg = '0;  // Clear all configuration
        
        // Set up a basic IPv4 filter rule for testing
        cfg_reg.filter_rules[0].ipv4_addr = 32'hC0A80001; // 192.168.0.1
        cfg_reg.filter_rules[0].ipv6_addr = 128'h0;       // Don't match IPv6
        cfg_reg.filter_rules[0].port = 32'h50;            // Port 80 (HTTP)
        
        cfg_reg.filter_rules[1].ipv4_addr = 32'h0;        // Match any IPv4
        cfg_reg.filter_rules[1].ipv6_addr = 128'h0;       // Don't match IPv6  
        cfg_reg.filter_rules[1].port = 32'h0;             // Match any port
    end
    
    // Initialize output ready
    initial begin
        m_axis_tready = 1'b1;  // Always ready for output
    end
    
    // Dump waves for debugging
    initial begin
        $dumpfile("filter_rx_pipeline.vcd");
        $dumpvars(0, tb_filter_rx_pipeline);
    end

endmodule
