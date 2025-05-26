// *************************************************************************
//
// Testbench wrapper for filter_rx_pipeline
// Flattens the cfg_reg structure for easier cocotb access
//
// *************************************************************************

`timescale 1ns / 1ps

import cfg_reg_pkg::*;
import packet_pkg::*;

module filter_rx_pipeline_tb (
    // Slave AXI Stream Interface (from adapter)
    input  wire        s_axis_tvalid,
    input  wire [511:0] s_axis_tdata,
    input  wire [63:0]  s_axis_tkeep,
    input  wire        s_axis_tlast,
    input  wire [47:0] s_axis_tuser,
    output wire        s_axis_tready,

    // Master AXI Stream Interface (to QDMA)
    output wire        m_axis_tvalid,
    output wire [511:0] m_axis_tdata,
    output wire [63:0]  m_axis_tkeep,
    output wire        m_axis_tlast,
    output wire [47:0] m_axis_tuser,
    input  wire        m_axis_tready,

    // Flattened configuration register inputs
    input  wire [31:0]  cfg_reg_filter_rules_0_ipv4_addr,
    input  wire [127:0] cfg_reg_filter_rules_0_ipv6_addr,
    input  wire [31:0]  cfg_reg_filter_rules_0_port,
    input  wire [31:0]  cfg_reg_filter_rules_1_ipv4_addr,
    input  wire [127:0] cfg_reg_filter_rules_1_ipv6_addr,
    input  wire [31:0]  cfg_reg_filter_rules_1_port,

    // Counter outputs (from DUT)
    output wire [31:0]  rule0_hit_count,
    output wire [31:0]  rule1_hit_count,
    output wire [31:0]  total_packets,
    output wire [31:0]  dropped_packets,

    // Clock and Reset
    input  wire        aclk,
    input  wire        aresetn
);

    // Pack configuration register structure
    cfg_reg_t cfg_reg_in;
    cfg_reg_t cfg_reg_out;
    
    assign cfg_reg_in.filter_rules[0].ipv4_addr = cfg_reg_filter_rules_0_ipv4_addr;
    assign cfg_reg_in.filter_rules[0].ipv6_addr = cfg_reg_filter_rules_0_ipv6_addr;
    assign cfg_reg_in.filter_rules[0].port = cfg_reg_filter_rules_0_port;
    assign cfg_reg_in.filter_rules[1].ipv4_addr = cfg_reg_filter_rules_1_ipv4_addr;
    assign cfg_reg_in.filter_rules[1].ipv6_addr = cfg_reg_filter_rules_1_ipv6_addr;
    assign cfg_reg_in.filter_rules[1].port = cfg_reg_filter_rules_1_port;
    
    // Initialize unused status inputs to 0
    assign cfg_reg_in.status.rule0_hit_count = 32'h0;
    assign cfg_reg_in.status.rule1_hit_count = 32'h0;
    assign cfg_reg_in.status.total_packets = 32'h0;
    assign cfg_reg_in.status.dropped_packets = 32'h0;

    // Extract status outputs
    assign rule0_hit_count = cfg_reg_out.status.rule0_hit_count;
    assign rule1_hit_count = cfg_reg_out.status.rule1_hit_count;
    assign total_packets = cfg_reg_out.status.total_packets;
    assign dropped_packets = cfg_reg_out.status.dropped_packets;

    // Instantiate DUT
    filter_rx_pipeline dut (
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tkeep(s_axis_tkeep),
        .s_axis_tlast(s_axis_tlast),
        .s_axis_tuser(s_axis_tuser),
        .s_axis_tready(s_axis_tready),
        
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tkeep(m_axis_tkeep),
        .m_axis_tlast(m_axis_tlast),
        .m_axis_tuser(m_axis_tuser),
        .m_axis_tready(m_axis_tready),
        
        .cfg_reg(cfg_reg_in),
        .cfg_reg_out(cfg_reg_out),
        
        .aclk(aclk),
        .aresetn(aresetn)
    );

    // Add some debug signals for visibility using p0/p1/p2 naming convention
    wire        p1_tvalid = dut.p1_tvalid;
    wire        p2_tvalid = dut.p2_tvalid;
    wire        p1_filter_pass = dut.p1_filter_pass;
    wire [1:0]  p1_rule_hit = dut.p1_rule_hit;
    wire        packet_in_progress = dut.packet_in_progress;
    wire        packet_start = dut.packet_start;
    wire        packet_end = dut.packet_end;
    
    // Legacy signal names for backwards compatibility with existing tests
    wire        stage1_tvalid = dut.p1_tvalid;
    wire        stage2_tvalid = dut.p2_tvalid;
    wire        stage1_filter_pass = dut.p1_filter_pass;
    wire [1:0]  stage1_rule_hit = dut.p1_rule_hit;

endmodule
