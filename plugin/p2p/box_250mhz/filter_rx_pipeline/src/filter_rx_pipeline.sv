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

    // Extract packet headers using struct-based parsing (big-endian)
    // Use p0_* signals for header extraction (input stage)
    
    // Cast 512-bit data to packet structures for easy field access
    eth_ipv4_pkt_t eth_ipv4_pkt;
    eth_ipv6_pkt_t eth_ipv6_pkt;
    
    assign eth_ipv4_pkt = eth_ipv4_pkt_t'(p0_tdata);
    assign eth_ipv6_pkt = eth_ipv6_pkt_t'(p0_tdata);
    
    // Extract Ethernet header (common for both IPv4 and IPv6)
    wire [47:0] eth_dst_mac  = eth_ipv4_pkt.eth.dst_mac;
    wire [47:0] eth_src_mac  = eth_ipv4_pkt.eth.src_mac;
    wire [15:0] eth_type     = eth_ipv4_pkt.eth.eth_type;

    // IPv4 header fields (using struct)
    wire [31:0] ipv4_src_ip   = eth_ipv4_pkt.ipv4.src_ip;
    wire [31:0] ipv4_dst_ip   = eth_ipv4_pkt.ipv4.dst_ip;
    wire [7:0]  ipv4_protocol = eth_ipv4_pkt.ipv4.protocol;

    // IPv6 header fields (using struct)
    wire [127:0] ipv6_src_ip    = eth_ipv6_pkt.ipv6.src_ip;
    wire [127:0] ipv6_dst_ip    = eth_ipv6_pkt.ipv6.dst_ip;
    wire [7:0]   ipv6_next_hdr  = eth_ipv6_pkt.ipv6.next_header;

    // TCP/UDP port fields (using struct)
    wire [15:0] ipv4_src_port = eth_ipv4_pkt.ports.src_port;
    wire [15:0] ipv4_dst_port = eth_ipv4_pkt.ports.dst_port;
    wire [15:0] ipv6_src_port = eth_ipv6_pkt.ports.src_port;
    wire [15:0] ipv6_dst_port = eth_ipv6_pkt.ports.dst_port;

    // Rule matching logic - only process IPv4 and IPv6 packets
    wire is_ipv4 = (eth_type == ETH_TYPE_IPV4);
    wire is_ipv6 = (eth_type == ETH_TYPE_IPV6);
    
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
            // IPv4 matching - Fixed to match destination IP and port (both must match when specified)
            assign rule_ipv4_ip_match[i] = is_ipv4 && 
                                          ((cfg_reg.filter_rules[i].ipv4_addr == 32'h0) || 
                                           (ipv4_dst_ip == cfg_reg.filter_rules[i].ipv4_addr));
            assign rule_ipv4_port_match[i] = is_ipv4 &&
                                            ((cfg_reg.filter_rules[i].port == 32'h0) || 
                                             (ipv4_dst_port == cfg_reg.filter_rules[i].port[15:0]));
            assign rule_ipv4_match[i] = rule_ipv4_ip_match[i] && rule_ipv4_port_match[i];

            // IPv6 matching - Fixed to match destination IP and port (both must match when specified)
            assign rule_ipv6_ip_match[i] = is_ipv6 && 
                                          ((cfg_reg.filter_rules[i].ipv6_addr == 128'h0) || 
                                           (ipv6_dst_ip == cfg_reg.filter_rules[i].ipv6_addr));
            assign rule_ipv6_port_match[i] = is_ipv6 &&
                                            ((cfg_reg.filter_rules[i].port == 32'h0) || 
                                             (ipv6_dst_port == cfg_reg.filter_rules[i].port[15:0]));
            assign rule_ipv6_match[i] = rule_ipv6_ip_match[i] && rule_ipv6_port_match[i];

            // Combined rule matching
            assign rule_match[i] = rule_ipv4_match[i] || rule_ipv6_match[i];
        end
    endgenerate

    // Overall filter match - only IPv4 and IPv6 packets can match rules
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
            if (packet_start && packet_end) begin
                // Single-cycle packet: start and end in same cycle, stay at 0
                packet_in_progress <= 1'b0;
            end else if (packet_start) begin
                // Multi-cycle packet start
                packet_in_progress <= 1'b1;
            end else if (packet_end) begin
                // Multi-cycle packet end
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

    // Debug: Print packet start and basic info
    always @(posedge aclk) begin
        if (p0_tvalid && s_axis_tready) begin
            if (packet_start) begin
                $display("[%0t] DEBUG: PACKET START", $time);
                $display("  Raw data[511:400]: 0x%03h", p0_tdata[511:400]);
                $display("  Raw data[415:400]: 0x%04h (EtherType field)", p0_tdata[415:400]);
                $display("  Raw data[511:448]: 0x%016h", p0_tdata[511:448]);
                $display("  EthType=0x%h, is_ipv4=%b, is_ipv6=%b", eth_type, is_ipv4, is_ipv6);
                $display("  Expected IPv4 EtherType: 0x0800");
                if (is_ipv4) begin
                    $display("  IPv4 Packet: dst_ip=0x%h (%d.%d.%d.%d), dst_port=%d", 
                             ipv4_dst_ip, ipv4_dst_ip[31:24], ipv4_dst_ip[23:16], ipv4_dst_ip[15:8], ipv4_dst_ip[7:0], ipv4_dst_port);
                    $display("  Rule 0: ipv4_addr=0x%h (%d.%d.%d.%d), port=%d", 
                             cfg_reg.filter_rules[0].ipv4_addr, 
                             cfg_reg.filter_rules[0].ipv4_addr[31:24], cfg_reg.filter_rules[0].ipv4_addr[23:16], 
                             cfg_reg.filter_rules[0].ipv4_addr[15:8], cfg_reg.filter_rules[0].ipv4_addr[7:0],
                             cfg_reg.filter_rules[0].port[15:0]);
                    $display("  Rule 0: ip_match=%b, port_match=%b, rule_match=%b", 
                             rule_ipv4_ip_match[0], rule_ipv4_port_match[0], rule_ipv4_match[0]);
                    $display("  Overall: filter_match=%b", filter_match);
                end else begin
                    $display("  Packet NOT recognized as IPv4!");
                end
            end
        end
    end

    // Additional debug for packet_start detection
    always @(posedge aclk) begin
        if (p0_tvalid && s_axis_tready) begin
            $display("[%0t] FILTER: p0_tvalid=%b, s_axis_tready=%b, packet_in_progress=%b, packet_start=%b, packet_end=%b", 
                     $time, p0_tvalid, s_axis_tready, packet_in_progress, packet_start, packet_end);
        end
    end

endmodule
