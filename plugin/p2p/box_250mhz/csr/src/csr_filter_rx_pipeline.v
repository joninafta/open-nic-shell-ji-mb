// *************************************************************************
//
// CSR Filter RX Pipeline Module
// Implements AXI-Lite slave interface with registers for two rules
// Each rule contains: IPv4 (32b), IPv6 (128b), Port (32b)
// Total per rule: 6 registers (192 bits)
//
// *************************************************************************

import cfg_reg_pkg::*;

module csr_filter_rx_pipeline #(
    parameter ADDR_WIDTH = 12,      // Address space width
    parameter REG_PREFIX = 16'hB000 // Register prefix for address matching
)(
    // AXI-Lite Slave Interface
    input  wire                    s_axil_awvalid,
    input  wire [ADDR_WIDTH-1:0]   s_axil_awaddr,
    output wire                    s_axil_awready,
    input  wire                    s_axil_wvalid,
    input  wire [31:0]             s_axil_wdata,
    output wire                    s_axil_wready,
    output wire                    s_axil_bvalid,
    output wire [1:0]              s_axil_bresp,
    input  wire                    s_axil_bready,
    input  wire                    s_axil_arvalid,
    input  wire [ADDR_WIDTH-1:0]   s_axil_araddr,
    output wire                    s_axil_arready,
    output wire                    s_axil_rvalid,
    output wire [31:0]             s_axil_rdata,
    output wire [1:0]              s_axil_rresp,
    input  wire                    s_axil_rready,

    // Configuration register output
    output cfg_reg_t               cfg_reg,

    // Clock and Reset
    input  wire                    aclk,
    input  wire                    aresetn
);

    // Internal configuration register storage
    cfg_reg_t cfg_reg_internal;

    // AXI-Lite state machine
    localparam IDLE = 2'b00, WRITE = 2'b01, READ = 2'b10;
    
    reg [1:0] state;
    reg [ADDR_WIDTH-1:0] write_addr;
    reg [ADDR_WIDTH-1:0] read_addr;
    reg [31:0] read_data;
    reg write_ready, read_ready;
    reg bvalid, rvalid;

    // Address matching logic
    wire addr_match_write = (s_axil_awaddr[31:ADDR_WIDTH] == REG_PREFIX[31:ADDR_WIDTH]);
    wire addr_match_read  = (s_axil_araddr[31:ADDR_WIDTH] == REG_PREFIX[31:ADDR_WIDTH]);

    // Connect internal config to output
    assign cfg_reg = cfg_reg_internal;

    // AXI-Lite interface logic
    assign s_axil_awready = (state == IDLE) && s_axil_awvalid && addr_match_write;
    assign s_axil_wready = write_ready;
    assign s_axil_bvalid = bvalid;
    assign s_axil_bresp = 2'b00; // OKAY
    assign s_axil_arready = (state == IDLE) && s_axil_arvalid && addr_match_read;
    assign s_axil_rvalid = rvalid;
    assign s_axil_rdata = read_data;
    assign s_axil_rresp = 2'b00; // OKAY

    always @(posedge aclk) begin
        if (!aresetn) begin
            state <= IDLE;
            write_addr <= 0;
            read_addr <= 0;
            read_data <= 0;
            write_ready <= 0;
            read_ready <= 0;
            bvalid <= 0;
            rvalid <= 0;
            
            // Reset all configuration registers
            cfg_reg_internal <= '0;
        end else begin
            case (state)
                IDLE: begin
                    bvalid <= 0;
                    rvalid <= 0;
                    write_ready <= 0;
                    
                    if (s_axil_awvalid && s_axil_awready) begin
                        write_addr <= s_axil_awaddr;
                        state <= WRITE;
                        write_ready <= 1;
                    end else if (s_axil_arvalid && s_axil_arready) begin
                        read_addr <= s_axil_araddr;
                        state <= READ;
                        read_ready <= 1;
                    end
                end
                
                WRITE: begin
                    if (s_axil_wvalid && s_axil_wready) begin
                        write_ready <= 0;
                        bvalid <= 1;
                        
                        // Write to registers based on address
                        case (write_addr[ADDR_WIDTH-1:2]) // Word address
                            RULE0_IPV4_OFFSET:    cfg_reg_internal.filter_rules[0].ipv4_addr <= s_axil_wdata;
                            RULE0_IPV6_0_OFFSET:  cfg_reg_internal.filter_rules[0].ipv6_addr[31:0] <= s_axil_wdata;
                            RULE0_IPV6_1_OFFSET:  cfg_reg_internal.filter_rules[0].ipv6_addr[63:32] <= s_axil_wdata;
                            RULE0_IPV6_2_OFFSET:  cfg_reg_internal.filter_rules[0].ipv6_addr[95:64] <= s_axil_wdata;
                            RULE0_IPV6_3_OFFSET:  cfg_reg_internal.filter_rules[0].ipv6_addr[127:96] <= s_axil_wdata;
                            RULE0_PORT_OFFSET:    cfg_reg_internal.filter_rules[0].port <= s_axil_wdata;
                            RULE1_IPV4_OFFSET:    cfg_reg_internal.filter_rules[1].ipv4_addr <= s_axil_wdata;
                            RULE1_IPV6_0_OFFSET:  cfg_reg_internal.filter_rules[1].ipv6_addr[31:0] <= s_axil_wdata;
                            RULE1_IPV6_1_OFFSET:  cfg_reg_internal.filter_rules[1].ipv6_addr[63:32] <= s_axil_wdata;
                            RULE1_IPV6_2_OFFSET:  cfg_reg_internal.filter_rules[1].ipv6_addr[95:64] <= s_axil_wdata;
                            RULE1_IPV6_3_OFFSET:  cfg_reg_internal.filter_rules[1].ipv6_addr[127:96] <= s_axil_wdata;
                            RULE1_PORT_OFFSET:    cfg_reg_internal.filter_rules[1].port <= s_axil_wdata;
                            default: ; // Ignore writes to undefined addresses
                        endcase
                    end
                    
                    if (bvalid && s_axil_bready) begin
                        bvalid <= 0;
                        state <= IDLE;
                    end
                end
                
                READ: begin
                    if (read_ready) begin
                        read_ready <= 0;
                        rvalid <= 1;
                        
                        // Read from registers based on address
                        case (read_addr[ADDR_WIDTH-1:2]) // Word address
                            RULE0_IPV4_OFFSET:    read_data <= cfg_reg_internal.filter_rules[0].ipv4_addr;
                            RULE0_IPV6_0_OFFSET:  read_data <= cfg_reg_internal.filter_rules[0].ipv6_addr[31:0];
                            RULE0_IPV6_1_OFFSET:  read_data <= cfg_reg_internal.filter_rules[0].ipv6_addr[63:32];
                            RULE0_IPV6_2_OFFSET:  read_data <= cfg_reg_internal.filter_rules[0].ipv6_addr[95:64];
                            RULE0_IPV6_3_OFFSET:  read_data <= cfg_reg_internal.filter_rules[0].ipv6_addr[127:96];
                            RULE0_PORT_OFFSET:    read_data <= cfg_reg_internal.filter_rules[0].port;
                            RULE1_IPV4_OFFSET:    read_data <= cfg_reg_internal.filter_rules[1].ipv4_addr;
                            RULE1_IPV6_0_OFFSET:  read_data <= cfg_reg_internal.filter_rules[1].ipv6_addr[31:0];
                            RULE1_IPV6_1_OFFSET:  read_data <= cfg_reg_internal.filter_rules[1].ipv6_addr[63:32];
                            RULE1_IPV6_2_OFFSET:  read_data <= cfg_reg_internal.filter_rules[1].ipv6_addr[95:64];
                            RULE1_IPV6_3_OFFSET:  read_data <= cfg_reg_internal.filter_rules[1].ipv6_addr[127:96];
                            RULE1_PORT_OFFSET:    read_data <= cfg_reg_internal.filter_rules[1].port;
                            // Status registers (read-only from external cfg_reg input)
                            RULE0_HIT_COUNT_OFFSET: read_data <= cfg_reg.status.rule0_hit_count;
                            RULE1_HIT_COUNT_OFFSET: read_data <= cfg_reg.status.rule1_hit_count;
                            TOTAL_PKT_COUNT_OFFSET: read_data <= cfg_reg.status.total_packets;
                            DROP_PKT_COUNT_OFFSET:  read_data <= cfg_reg.status.dropped_packets;
                            default: read_data <= 32'h0;
                        endcase
                    end
                    
                    if (rvalid && s_axil_rready) begin
                        rvalid <= 0;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end

endmodule
