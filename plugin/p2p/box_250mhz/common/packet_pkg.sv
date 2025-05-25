// *************************************************************************
//
// Packet Package
// Defines packet header structures for Ethernet, IPv4, and IPv6
// Assumes big-endian byte ordering
//
// *************************************************************************

`timescale 1ns / 1ps

package packet_pkg;

    // Ethernet header structure (14 bytes)
    typedef struct packed {
        logic [47:0] dst_mac;     // Destination MAC address
        logic [47:0] src_mac;     // Source MAC address  
        logic [15:0] eth_type;    // EtherType (0x0800 = IPv4, 0x86DD = IPv6)
    } eth_hdr_t;

    // IPv4 header structure (20 bytes minimum)
    typedef struct packed {
        logic [3:0]  version;     // IP version (4)
        logic [3:0]  ihl;         // Internet Header Length
        logic [7:0]  tos;         // Type of Service
        logic [15:0] length;      // Total Length
        logic [15:0] id;          // Identification
        logic [2:0]  flags;       // Flags
        logic [12:0] frag_offset; // Fragment Offset
        logic [7:0]  ttl;         // Time to Live
        logic [7:0]  protocol;    // Protocol (6=TCP, 17=UDP)
        logic [15:0] checksum;    // Header Checksum
        logic [31:0] src_ip;      // Source IP Address
        logic [31:0] dst_ip;      // Destination IP Address
    } ipv4_hdr_t;

    // IPv6 header structure (40 bytes)
    typedef struct packed {
        logic [3:0]   version;      // IP version (6)
        logic [7:0]   traffic_class; // Traffic Class
        logic [19:0]  flow_label;   // Flow Label
        logic [15:0]  payload_len;  // Payload Length
        logic [7:0]   next_header;  // Next Header (6=TCP, 17=UDP)
        logic [7:0]   hop_limit;    // Hop Limit
        logic [127:0] src_ip;       // Source IP Address
        logic [127:0] dst_ip;       // Destination IP Address
    } ipv6_hdr_t;

    // TCP/UDP port structure
    typedef struct packed {
        logic [15:0] src_port;    // Source port
        logic [15:0] dst_port;    // Destination port
    } port_hdr_t;

    // Union for IP headers
    typedef union packed {
        ipv4_hdr_t ipv4;
        ipv6_hdr_t ipv6;
    } ip_hdr_u;

    // Complete packet header structure
    typedef struct packed {
        eth_hdr_t  eth;
        ip_hdr_u   ip;
        port_hdr_t ports;
    } pkt_hdr_t;

    // EtherType constants
    parameter logic [15:0] ETH_TYPE_IPV4 = 16'h0800;
    parameter logic [15:0] ETH_TYPE_IPV6 = 16'h86DD;

    // IP Protocol constants
    parameter logic [7:0] IP_PROTO_TCP = 8'h06;
    parameter logic [7:0] IP_PROTO_UDP = 8'h11;

    // Bit offset constants for 512-bit data bus (big-endian)
    // Ethernet header offsets (starts at byte 0)
    localparam ETH_DST_MAC_MSB     = 511;
    localparam ETH_DST_MAC_LSB     = 464;
    localparam ETH_SRC_MAC_MSB     = 463;
    localparam ETH_SRC_MAC_LSB     = 416;
    localparam ETH_TYPE_MSB        = 415;
    localparam ETH_TYPE_LSB        = 400;

    // IPv4 header offsets (starts at byte 14)
    localparam IPV4_PROTOCOL_MSB   = 328;
    localparam IPV4_PROTOCOL_LSB   = 321;
    localparam IPV4_SRC_IP_MSB     = 335;
    localparam IPV4_SRC_IP_LSB     = 304;
    localparam IPV4_DST_IP_MSB     = 303;
    localparam IPV4_DST_IP_LSB     = 272;

    // IPv6 header offsets (starts at byte 14)
    localparam IPV6_NEXT_HDR_MSB   = 280;
    localparam IPV6_NEXT_HDR_LSB   = 273;
    localparam IPV6_SRC_IP_MSB     = 399;
    localparam IPV6_SRC_IP_LSB     = 272;
    localparam IPV6_DST_IP_MSB     = 271;
    localparam IPV6_DST_IP_LSB     = 144;

    // TCP/UDP port offsets
    // IPv4: ports start at byte 34
    localparam IPV4_SRC_PORT_MSB   = 271;
    localparam IPV4_SRC_PORT_LSB   = 256;
    localparam IPV4_DST_PORT_MSB   = 255;
    localparam IPV4_DST_PORT_LSB   = 240;

    // IPv6: ports start at byte 54
    localparam IPV6_SRC_PORT_MSB   = 143;
    localparam IPV6_SRC_PORT_LSB   = 128;
    localparam IPV6_DST_PORT_MSB   = 127;
    localparam IPV6_DST_PORT_LSB   = 112;

endpackage
