// *************************************************************************
//
// Simple packet generator module for testbench
// Generates basic Ethernet packets with configurable headers
//
// *************************************************************************

`timescale 1ns / 1ps

module packet_generator (
    input wire clk,
    input wire reset_n,
    input wire enable,
    input wire [31:0] src_ip,
    input wire [31:0] dst_ip,
    input wire [15:0] src_port,
    input wire [15:0] dst_port,
    input wire [15:0] packet_length,
    input wire ipv6_mode,
    input wire [127:0] src_ipv6,
    input wire [127:0] dst_ipv6,
    output reg m_axis_tvalid,
    output reg [511:0] m_axis_tdata,
    output reg [63:0] m_axis_tkeep,
    output reg m_axis_tlast,
    output reg [47:0] m_axis_tuser,
    input wire m_axis_tready
);

    typedef enum logic [2:0] {
        IDLE,
        SEND_PACKET,
        WAIT_READY
    } state_t;
    
    state_t state, next_state;
    reg [7:0] packet_count;
    
    // Build realistic packet data
    reg [511:0] packet_data;
    
    always_comb begin
        if (ipv6_mode) begin
            // IPv6 packet structure (simplified)
            packet_data = {
                // Ethernet header (14 bytes)
                48'hDEADBEEFCAFE,    // Dst MAC
                48'h123456789ABC,    // Src MAC  
                16'h86DD,            // EtherType (IPv6)
                
                // IPv6 header (40 bytes)
                32'h60000000,        // Version, Traffic Class, Flow Label
                16'h0028,            // Payload Length
                8'h11,               // Next Header (UDP)
                8'h40,               // Hop Limit
                src_ipv6,            // Source Address
                dst_ipv6,            // Destination Address
                
                // UDP header (8 bytes)
                src_port,            // Source Port
                dst_port,            // Destination Port
                16'h0008,            // Length
                16'h0000,            // Checksum
                
                // Padding
                288'h0
            };
        end else begin
            // IPv4 packet structure
            packet_data = {
                // Ethernet header (14 bytes)
                48'hDEADBEEFCAFE,    // Dst MAC
                48'h123456789ABC,    // Src MAC
                16'h0800,            // EtherType (IPv4)
                
                // IPv4 header (20 bytes)
                8'h45,               // Version + IHL
                8'h00,               // ToS
                16'h001C,            // Total Length
                16'h1234,            // Identification
                16'h4000,            // Flags + Fragment Offset
                8'h40,               // TTL
                8'h11,               // Protocol (UDP)
                16'h0000,            // Header Checksum
                src_ip,              // Source IP
                dst_ip,              // Destination IP
                
                // UDP header (8 bytes)
                src_port,            // Source Port
                dst_port,            // Destination Port
                16'h0008,            // Length
                16'h0000,            // Checksum
                
                // Padding
                352'h0
            };
        end
    end
    
    // State machine
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state <= IDLE;
            packet_count <= 0;
        end else begin
            state <= next_state;
            if (state == SEND_PACKET && m_axis_tready) begin
                packet_count <= packet_count + 1;
            end
        end
    end
    
    always_comb begin
        next_state = state;
        case (state)
            IDLE: begin
                if (enable) next_state = SEND_PACKET;
            end
            SEND_PACKET: begin
                if (m_axis_tready) next_state = WAIT_READY;
            end
            WAIT_READY: begin
                if (!enable) next_state = IDLE;
            end
        endcase
    end
    
    // Output assignments
    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            m_axis_tvalid <= 0;
            m_axis_tdata <= 0;
            m_axis_tkeep <= 0;
            m_axis_tlast <= 0;
            m_axis_tuser <= 0;
        end else begin
            case (state)
                IDLE: begin
                    m_axis_tvalid <= 0;
                    m_axis_tlast <= 0;
                end
                SEND_PACKET: begin
                    if (m_axis_tready) begin
                        m_axis_tvalid <= 1;
                        m_axis_tdata <= packet_data;
                        m_axis_tkeep <= 64'hFFFFFFFFFFFFFFFF;
                        m_axis_tlast <= 1;
                        m_axis_tuser <= 48'h0;
                    end
                end
                WAIT_READY: begin
                    m_axis_tvalid <= 0;
                    m_axis_tlast <= 0;
                end
            endcase
        end
    end

endmodule
