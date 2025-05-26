// *************************************************************************
//
// Filter RX Pipeline Module
// Implements packet filtering based on IPv4, IPv6, and port rules
// Same interface as axi_stream_pipeline but with filtering logic
//
// Assumptions:
// - Packets are always Ethernet (no VLAN tags)
// - After Ethernet header, there's either IPv4 or IPv6
// - Big-endian byte ordering
// - Packets start with tvalid and end with tlast
//
// *************************************************************************

`timescale 1ns / 1ps

import cfg_reg_pkg::*;
import packet_pkg::*;

module filter_rx_pipeline (
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

    // Configuration register input
    input  cfg_reg_t   cfg_reg,

    // Configuration register output (status)
    output cfg_reg_t   cfg_reg_out,

    // Clock and Reset
    input  wire        aclk,
    input  wire        aresetn
);

    // Pipeline stage signals using p0/p1/p2 convention
    // p0_* : Input stage (before sampling - s_axis signals)
    wire        p0_tvalid = s_axis_tvalid;
    wire [511:0] p0_tdata = s_axis_tdata;
    wire [63:0]  p0_tkeep = s_axis_tkeep;
    wire        p0_tlast = s_axis_tlast;
    wire [47:0] p0_tuser = s_axis_tuser;

    // p1_* : First pipeline stage
    reg        p1_tvalid;
    reg [511:0] p1_tdata;
    reg [63:0]  p1_tkeep;
    reg        p1_tlast;
    reg [47:0] p1_tuser;
    reg        p1_filter_pass;
    reg [1:0]  p1_rule_hit;  // Which rule was hit (0, 1, or none)

    // p2_* : Second pipeline stage
    reg        p2_tvalid;
    reg [511:0] p2_tdata;
    reg [63:0]  p2_tkeep;
    reg        p2_tlast;
    reg [47:0] p2_tuser;

    // Packet status counters
    reg [31:0] rule0_hit_count;
    reg [31:0] rule1_hit_count;
    reg [31:0] total_packets;
    reg [31:0] dropped_packets;

    // Assign status registers to output
    assign cfg_reg_out.status.rule0_hit_count = rule0_hit_count;
    assign cfg_reg_out.status.rule1_hit_count = rule1_hit_count;
    assign cfg_reg_out.status.total_packets = total_packets;
    assign cfg_reg_out.status.dropped_packets = dropped_packets;
    
    // Pass through input configuration to output
    assign cfg_reg_out.filter_rules = cfg_reg.filter_rules;

    // Extract packet headers using defined bit offsets (big-endian)
    // Use p0_* signals for header extraction (input stage)
    // Ethernet header
    wire [47:0] eth_dst_mac  = p0_tdata[ETH_DST_MAC_MSB:ETH_DST_MAC_LSB];
    wire [47:0] eth_src_mac  = p0_tdata[ETH_SRC_MAC_MSB:ETH_SRC_MAC_LSB];
    wire [15:0] eth_type     = p0_tdata[ETH_TYPE_MSB:ETH_TYPE_LSB];

    // IPv4 header fields
    wire [31:0] ipv4_src_ip  = p0_tdata[IPV4_SRC_IP_MSB:IPV4_SRC_IP_LSB];
    wire [31:0] ipv4_dst_ip  = p0_tdata[IPV4_DST_IP_MSB:IPV4_DST_IP_LSB];
    wire [7:0]  ipv4_protocol = p0_tdata[IPV4_PROTOCOL_MSB:IPV4_PROTOCOL_LSB];

    // IPv6 header fields
    wire [127:0] ipv6_src_ip = p0_tdata[IPV6_SRC_IP_MSB:IPV6_SRC_IP_LSB];
    wire [127:0] ipv6_dst_ip = p0_tdata[IPV6_DST_IP_MSB:IPV6_DST_IP_LSB];
    wire [7:0]   ipv6_next_hdr = p0_tdata[IPV6_NEXT_HDR_MSB:IPV6_NEXT_HDR_LSB];

    // TCP/UDP port fields
    wire [15:0] ipv4_src_port = p0_tdata[IPV4_SRC_PORT_MSB:IPV4_SRC_PORT_LSB];
    wire [15:0] ipv4_dst_port = p0_tdata[IPV4_DST_PORT_MSB:IPV4_DST_PORT_LSB];
    wire [15:0] ipv6_src_port = p0_tdata[IPV6_SRC_PORT_MSB:IPV6_SRC_PORT_LSB];
    wire [15:0] ipv6_dst_port = p0_tdata[IPV6_DST_PORT_MSB:IPV6_DST_PORT_LSB];

    // Rule matching logic
    wire is_ipv4 = (eth_type == ETH_TYPE_IPV4);
    wire is_ipv6 = (eth_type == ETH_TYPE_IPV6);
    
    // Rule 0 matching
    wire rule0_ipv4_ip_match = is_ipv4 && 
                              ((cfg_reg.filter_rules[0].ipv4_addr == 32'h0) || 
                               (ipv4_src_ip == cfg_reg.filter_rules[0].ipv4_addr));
    wire rule0_ipv4_port_match = is_ipv4 && 
                                ((cfg_reg.filter_rules[0].port == 32'h0) || 
                                 (ipv4_src_port == cfg_reg.filter_rules[0].port[15:0]));
    wire rule0_ipv4_match = rule0_ipv4_ip_match || rule0_ipv4_port_match;

    wire rule0_ipv6_ip_match = is_ipv6 && 
                              ((cfg_reg.filter_rules[0].ipv6_addr == 128'h0) || 
                               (ipv6_src_ip == cfg_reg.filter_rules[0].ipv6_addr));
    wire rule0_ipv6_port_match = is_ipv6 && 
                                ((cfg_reg.filter_rules[0].port == 32'h0) || 
                                 (ipv6_src_port == cfg_reg.filter_rules[0].port[15:0]));
    wire rule0_ipv6_match = rule0_ipv6_ip_match || rule0_ipv6_port_match;

    wire rule0_match = rule0_ipv4_match || rule0_ipv6_match;

    // Rule 1 matching
    wire rule1_ipv4_ip_match = is_ipv4 && 
                              ((cfg_reg.filter_rules[1].ipv4_addr == 32'h0) || 
                               (ipv4_src_ip == cfg_reg.filter_rules[1].ipv4_addr));
    wire rule1_ipv4_port_match = is_ipv4 && 
                                ((cfg_reg.filter_rules[1].port == 32'h0) || 
                                 (ipv4_src_port == cfg_reg.filter_rules[1].port[15:0]));
    wire rule1_ipv4_match = rule1_ipv4_ip_match || rule1_ipv4_port_match;

    wire rule1_ipv6_ip_match = is_ipv6 && 
                              ((cfg_reg.filter_rules[1].ipv6_addr == 128'h0) || 
                               (ipv6_src_ip == cfg_reg.filter_rules[1].ipv6_addr));
    wire rule1_ipv6_port_match = is_ipv6 && 
                                ((cfg_reg.filter_rules[1].port == 32'h0) || 
                                 (ipv6_src_port == cfg_reg.filter_rules[1].port[15:0]));
    wire rule1_ipv6_match = rule1_ipv6_ip_match || rule1_ipv6_port_match;

    wire rule1_match = rule1_ipv4_match || rule1_ipv6_match;

    wire filter_match = rule0_match || rule1_match;
    wire [1:0] rule_hit = rule0_match ? 2'b01 : (rule1_match ? 2'b10 : 2'b00);

    // Flow control using p1/p2 naming convention
    wire p1_ready = !p1_tvalid || p2_ready;
    wire p2_ready = !p2_tvalid || m_axis_tready;
    
    assign s_axis_tready = p1_ready;

    // Packet start detection (first beat of a packet)
    reg packet_in_progress;
    wire packet_start = p0_tvalid && s_axis_tready && !packet_in_progress;
    wire packet_end = p0_tvalid && s_axis_tready && p0_tlast;

    always @(posedge aclk) begin
        if (!aresetn) begin
            packet_in_progress <= 1'b0;
        end else begin
            if (packet_start) begin
                packet_in_progress <= 1'b1;
            end else if (packet_end) begin
                packet_in_progress <= 1'b0;
            end
        end
    end

    // Packet status counters
    always @(posedge aclk) begin
        if (!aresetn) begin
            rule0_hit_count <= 32'h0;
            rule1_hit_count <= 32'h0;
            total_packets <= 32'h0;
            dropped_packets <= 32'h0;
        end else begin
            if (packet_start) begin
                total_packets <= total_packets + 1;
                if (rule0_match && !rule1_match) begin
                    rule0_hit_count <= rule0_hit_count + 1;
                end else if (rule1_match && !rule0_match) begin
                    rule1_hit_count <= rule1_hit_count + 1;
                end else if (rule0_match && rule1_match) begin
                    // Both rules match - count for rule 0 (priority)
                    rule0_hit_count <= rule0_hit_count + 1;
                end else begin
                    dropped_packets <= dropped_packets + 1;
                end
            end
        end
    end

    // Pipeline Stage 1: Filtering decision (only sample on packet start)
    always @(posedge aclk) begin
        if (!aresetn) begin
            p1_tvalid <= 1'b0;
        end else begin
            if (p1_ready) begin
                p1_tvalid <= p0_tvalid;
                p1_tdata <= p0_tdata;
                p1_tkeep <= p0_tkeep;
                p1_tlast <= p0_tlast;
                p1_tuser <= p0_tuser;
                // Only evaluate filter on packet start, maintain decision for rest of packet
                if (packet_start) begin
                    p1_filter_pass <= filter_match;
                    p1_rule_hit <= rule_hit;
                end
            end
        end
    end

    // Pipeline Stage 2: Output stage
    always @(posedge aclk) begin
        if (!aresetn) begin
            p2_tvalid <= 1'b0;
        end else begin
            if (p2_ready) begin
                p2_tvalid <= p1_tvalid && p1_filter_pass;
                p2_tdata <= p1_tdata;
                p2_tkeep <= p1_tkeep;
                p2_tlast <= p1_tlast;
                p2_tuser <= p1_tuser;
            end
        end
    end

    // Output assignments
    assign m_axis_tvalid = p2_tvalid;
    assign m_axis_tdata = p2_tdata;
    assign m_axis_tkeep = p2_tkeep;
    assign m_axis_tlast = p2_tlast;
    assign m_axis_tuser = p2_tuser;

    // Debug: Print each packet being written to QDMA
    always @(posedge aclk) begin
        if (m_axis_tvalid && m_axis_tready && m_axis_tlast) begin
            $display("[%0t] PACKET TO QDMA: Rule hit = %0d, Data = 0x%h", 
                     $time, p1_rule_hit, p2_tdata[63:0]);
        end
    end

endmodule
