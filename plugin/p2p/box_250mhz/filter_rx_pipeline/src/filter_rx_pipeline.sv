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

module filter_rx_pipeline #(
    parameter NUM_RULES = 2  // Configurable number of filter rules
) (
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
    output status_reg_t   status_reg,

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

    // Packet status counters - now parameterized
    reg [31:0] rule_hit_count [NUM_RULES-1:0];
    reg [31:0] total_packets;
    reg [31:0] dropped_packets;

    // Assign status registers to output (assuming status_reg supports variable rules)
    genvar k;
    generate
        for (k = 0; k < NUM_RULES; k = k + 1) begin : gen_status_assign
            if (k == 0) assign status_reg.rule0_hit_count = rule_hit_count[0];
            if (k == 1) assign status_reg.rule1_hit_count = rule_hit_count[1];
        end
    endgenerate
    assign status_reg.total_packets = total_packets;
    assign status_reg.dropped_packets = dropped_packets;

    // Extract packet headers using defined bit offsets (big-endian)
    // Use p0_* signals for header extraction (input stage)
    // Ethernet header
    wire [47:0] eth_dst_mac  = p0_tdata[ETH_DST_MAC_MSB:ETH_DST_MAC_LSB];
    wire [47:0] eth_src_mac  = p0_tdata[ETH_SRC_MAC_MSB:ETH_SRC_MAC_LSB];
    wire [15:0] eth_type     = p0_tdata[ETH_TYPE_MSB:ETH_TYPE_LSB];

    // Check for VLAN tags - ensure this is untagged Ethernet only
    // VLAN tagged frames have 0x8100 (802.1Q) or 0x88A8 (802.1ad) in EtherType field
    wire has_vlan_tag = (eth_type == 16'h8100) ||  // 802.1Q VLAN tag
                       (eth_type == 16'h88A8) ||  // 802.1ad Service VLAN tag
                       (eth_type == 16'h9100) ||  // Legacy QinQ
                       (eth_type == 16'h9200);    // Legacy QinQ variant
    
    // Only process untagged Ethernet frames
    wire eth_untagged_valid = !has_vlan_tag;

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

    // Rule matching logic - parameterized with validation (untagged Ethernet only)
    wire is_ipv4 = eth_untagged_valid && (eth_type == ETH_TYPE_IPV4);
    wire is_ipv6 = eth_untagged_valid && (eth_type == ETH_TYPE_IPV6);
    
    // Arrays for rule matching signals
    wire [NUM_RULES-1:0] rule_ipv4_ip_match;
    wire [NUM_RULES-1:0] rule_ipv4_port_match;
    wire [NUM_RULES-1:0] rule_ipv4_match;
    wire [NUM_RULES-1:0] rule_ipv6_ip_match;
    wire [NUM_RULES-1:0] rule_ipv6_port_match;
    wire [NUM_RULES-1:0] rule_ipv6_match;
    wire [NUM_RULES-1:0] rule_match;

    // Generate rule matching logic for each rule
    genvar i;
    generate
        for (i = 0; i < NUM_RULES; i = i + 1) begin : gen_rule_match
            // IPv4 matching
            assign rule_ipv4_ip_match[i] = is_ipv4 && 
                                          ((cfg_reg.filter_rules[i].ipv4_addr == 32'h0) || 
                                           (ipv4_src_ip == cfg_reg.filter_rules[i].ipv4_addr));
            assign rule_ipv4_port_match[i] = is_ipv4 &&
                                            ((cfg_reg.filter_rules[i].port == 32'h0) || 
                                             (ipv4_src_port == cfg_reg.filter_rules[i].port[15:0]));
            assign rule_ipv4_match[i] = rule_ipv4_ip_match[i] || rule_ipv4_port_match[i];

            // IPv6 matching
            assign rule_ipv6_ip_match[i] = is_ipv6 && 
                                          ((cfg_reg.filter_rules[i].ipv6_addr == 128'h0) || 
                                           (ipv6_src_ip == cfg_reg.filter_rules[i].ipv6_addr));
            assign rule_ipv6_port_match[i] = is_ipv6 &&
                                            ((cfg_reg.filter_rules[i].port == 32'h0) || 
                                             (ipv6_src_port == cfg_reg.filter_rules[i].port[15:0]));
            assign rule_ipv6_match[i] = rule_ipv6_ip_match[i] || rule_ipv6_port_match[i];

            // Combined rule matching
            assign rule_match[i] = rule_ipv4_match[i] || rule_ipv6_match[i];
        end
    endgenerate

    // Overall filter match (OR of all rules)
    wire filter_match = (is_ipv4 || is_ipv6) && (|rule_match);

    // Priority encoder for rule hit (lowest index has highest priority)
    reg [$clog2(NUM_RULES+1)-1:0] rule_hit_encoded;
    always @(*) begin
        rule_hit_encoded = 0;
        for (int j = 0; j < NUM_RULES; j = j + 1) begin
            if (rule_match[j]) begin
                rule_hit_encoded = $clog2(NUM_RULES+1)'(j + 1);  // Proper width casting
                break;
            end
        end
    end

    wire [1:0] rule_hit = rule_hit_encoded[1:0];  // Maintain 2-bit width for compatibility

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

    // Packet status counters - parameterized
    always @(posedge aclk) begin
        if (!aresetn) begin
            for (int m = 0; m < NUM_RULES; m = m + 1) begin
                rule_hit_count[m] <= 32'h0;
            end
            total_packets <= 32'h0;
            dropped_packets <= 32'h0;
        end else begin
            if (packet_start) begin
                total_packets <= total_packets + 1;
                if (filter_match) begin
                    // Increment counter for the highest priority matching rule
                    if (rule_hit_encoded > 0) begin
                        rule_hit_count[rule_hit_encoded - 1] <= rule_hit_count[rule_hit_encoded - 1] + 1;
                    end
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
    assign m_axis_tvalid = '0;//p1_tvalid;
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
