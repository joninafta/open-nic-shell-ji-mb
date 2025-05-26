// *************************************************************************
//
// Enhanced packet sink module for testbench
// Receives, counts, and prints detailed packet information from the DUT
//
// *************************************************************************

`timescale 1ns / 1ps

import packet_pkg::*;

module packet_sink (
    input wire clk,
    input wire reset_n,
    input wire s_axis_tvalid,
    input wire [511:0] s_axis_tdata,
    input wire [63:0] s_axis_tkeep,
    input wire s_axis_tlast,
    input wire [47:0] s_axis_tuser,
    output wire s_axis_tready,
    output reg [31:0] packets_received
);

    assign s_axis_tready = 1'b1;  // Always ready
    
    // Packet counter
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            packets_received <= 0;
        end else if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
            packets_received <= packets_received + 1;
        end
    end
    
    // Packet printing logic - Enhanced with detailed information
    always_ff @(posedge clk) begin
        if (reset_n && s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tlast) begin
                // Always print packet completion summary
                print_packet_summary();
            end
`ifdef VERBOSE_PACKET_PRINT
            // Print each flit (beat) of the packet only in verbose mode
            print_packet_flit();
`endif
        end
    end
    
    // Function to print packet flit information
    function void print_packet_flit();
        $display("[%0t] PACKET FLIT: valid=%b, ready=%b, last=%b", 
                 $time, s_axis_tvalid, s_axis_tready, s_axis_tlast);
        $display("         Data: 0x%128h", s_axis_tdata);
        $display("         Keep: 0x%16h", s_axis_tkeep);
        $display("         User: 0x%12h", s_axis_tuser);
    endfunction
    
    // Function to print packet summary with parsed header information
    function void print_packet_summary();
        logic [47:0] eth_dst_mac, eth_src_mac;
        logic [15:0] eth_type;
        logic [31:0] ipv4_src, ipv4_dst;
        logic [127:0] ipv6_src, ipv6_dst;
        logic [15:0] src_port, dst_port;
        logic [7:0] ip_protocol;
        logic is_ipv4, is_ipv6, is_tcp, is_udp;
        
        // Parse Ethernet header (assuming first 64 bytes are in first flit)
        eth_dst_mac = s_axis_tdata[ETH_DST_MAC_MSB:ETH_DST_MAC_LSB];
        eth_src_mac = s_axis_tdata[ETH_SRC_MAC_MSB:ETH_SRC_MAC_LSB];
        eth_type = s_axis_tdata[ETH_TYPE_MSB:ETH_TYPE_LSB];
        
        is_ipv4 = (eth_type == ETH_TYPE_IPV4);
        is_ipv6 = (eth_type == ETH_TYPE_IPV6);
        
        $display("");
        $display("========== PACKET LEAVING DUT ==========");
        $display("[%0t] Packet #%0d received from DUT", $time, packets_received + 1);
        $display("Ethernet Header:");
        $display("  DST MAC: %02x:%02x:%02x:%02x:%02x:%02x", 
                 eth_dst_mac[47:40], eth_dst_mac[39:32], eth_dst_mac[31:24],
                 eth_dst_mac[23:16], eth_dst_mac[15:8], eth_dst_mac[7:0]);
        $display("  SRC MAC: %02x:%02x:%02x:%02x:%02x:%02x", 
                 eth_src_mac[47:40], eth_src_mac[39:32], eth_src_mac[31:24],
                 eth_src_mac[23:16], eth_src_mac[15:8], eth_src_mac[7:0]);
        $display("  Type: 0x%04x (%s)", eth_type, 
                 is_ipv4 ? "IPv4" : is_ipv6 ? "IPv6" : "Other");
        
        if (is_ipv4) begin
            // Parse IPv4 header
            ipv4_src = s_axis_tdata[IPV4_SRC_IP_MSB:IPV4_SRC_IP_LSB];
            ipv4_dst = s_axis_tdata[IPV4_DST_IP_MSB:IPV4_DST_IP_LSB];
            ip_protocol = s_axis_tdata[IPV4_PROTOCOL_MSB:IPV4_PROTOCOL_LSB];
            
            is_tcp = (ip_protocol == IP_PROTO_TCP);
            is_udp = (ip_protocol == IP_PROTO_UDP);
            
            $display("IPv4 Header:");
            $display("  SRC IP: %0d.%0d.%0d.%0d", 
                     ipv4_src[31:24], ipv4_src[23:16], ipv4_src[15:8], ipv4_src[7:0]);
            $display("  DST IP: %0d.%0d.%0d.%0d", 
                     ipv4_dst[31:24], ipv4_dst[23:16], ipv4_dst[15:8], ipv4_dst[7:0]);
            $display("  Protocol: %0d (%s)", ip_protocol,
                     is_tcp ? "TCP" : is_udp ? "UDP" : "Other");
            
            if (is_tcp || is_udp) begin
                src_port = s_axis_tdata[IPV4_SRC_PORT_MSB:IPV4_SRC_PORT_LSB];
                dst_port = s_axis_tdata[IPV4_DST_PORT_MSB:IPV4_DST_PORT_LSB];
                $display("  SRC Port: %0d", src_port);
                $display("  DST Port: %0d", dst_port);
            end
        end else if (is_ipv6) begin
            // Parse IPv6 header
            ipv6_src = s_axis_tdata[IPV6_SRC_IP_MSB:IPV6_SRC_IP_LSB];
            ipv6_dst = s_axis_tdata[IPV6_DST_IP_MSB:IPV6_DST_IP_LSB];
            ip_protocol = s_axis_tdata[IPV6_NEXT_HDR_MSB:IPV6_NEXT_HDR_LSB];
            
            is_tcp = (ip_protocol == IP_PROTO_TCP);
            is_udp = (ip_protocol == IP_PROTO_UDP);
            
            $display("IPv6 Header:");
            $display("  SRC IP: %04x:%04x:%04x:%04x:%04x:%04x:%04x:%04x",
                     ipv6_src[127:112], ipv6_src[111:96], ipv6_src[95:80], ipv6_src[79:64],
                     ipv6_src[63:48], ipv6_src[47:32], ipv6_src[31:16], ipv6_src[15:0]);
            $display("  DST IP: %04x:%04x:%04x:%04x:%04x:%04x:%04x:%04x",
                     ipv6_dst[127:112], ipv6_dst[111:96], ipv6_dst[95:80], ipv6_dst[79:64],
                     ipv6_dst[63:48], ipv6_dst[47:32], ipv6_dst[31:16], ipv6_dst[15:0]);
            $display("  Next Header: %0d (%s)", ip_protocol,
                     is_tcp ? "TCP" : is_udp ? "UDP" : "Other");
            
            if (is_tcp || is_udp) begin
                src_port = s_axis_tdata[IPV6_SRC_PORT_MSB:IPV6_SRC_PORT_LSB];
                dst_port = s_axis_tdata[IPV6_DST_PORT_MSB:IPV6_DST_PORT_LSB];
                $display("  SRC Port: %0d", src_port);
                $display("  DST Port: %0d", dst_port);
            end
        end
        
        $display("Packet Size: %0d bytes (estimated from tkeep)", count_packet_bytes());
        $display("User Data: 0x%012h", s_axis_tuser);
`ifdef VERBOSE_PACKET_PRINT
        $display("Raw tkeep: 0x%016h", s_axis_tkeep);
        $display("Timestamp: %0t", $time);
`endif
        $display("==========================================");
        $display("");
    endfunction
    
    // Function to estimate packet size from tkeep
    function int count_packet_bytes();
        int byte_count = 0;
        for (int i = 0; i < 64; i++) begin
            if (s_axis_tkeep[i]) byte_count++;
        end
        return byte_count;
    endfunction

endmodule
