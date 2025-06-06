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

    // IPv4 header structure (20 bytes minimum, padded to match IPv6 size)
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
        logic [159:0] padding;    // Padding to match IPv6 header size (40 bytes total)
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

    // Ethernet + IPv4 packet structure (for struct-based parsing)
    typedef struct packed {
        eth_hdr_t   eth;      // 14 bytes: Ethernet header
        ipv4_hdr_t  ipv4;     // 20 bytes: IPv4 header
        port_hdr_t  ports;    // 4 bytes: TCP/UDP ports
        logic [447:0] payload; // Remaining payload to fill 512 bits (56 bytes)
    } eth_ipv4_pkt_t;

    // Ethernet + IPv6 packet structure (for struct-based parsing)
    typedef struct packed {
        eth_hdr_t   eth;      // 14 bytes: Ethernet header
        ipv6_hdr_t  ipv6;     // 40 bytes: IPv6 header
        port_hdr_t  ports;    // 4 bytes: TCP/UDP ports
        logic [95:0] payload; // Remaining payload to fill 512 bits (12 bytes)
    } eth_ipv6_pkt_t;

    // EtherType constants
    localparam logic [15:0] ETH_TYPE_IPV4 = 16'h0800;
    localparam logic [15:0] ETH_TYPE_IPV6 = 16'h86DD;

    // IP Protocol constants
    localparam logic [7:0] IP_PROTO_TCP = 8'h06;
    localparam logic [7:0] IP_PROTO_UDP = 8'h11;

endpackage
