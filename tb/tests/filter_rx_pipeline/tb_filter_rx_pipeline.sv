/**
 * SystemVerilog testbench wrapper for filter_rx_pipeline
 * This provides the DUT instantiation for Cocotb testing
 */

`timescale 1ns / 1ps

module tb_filter_rx_pipeline;

    // Clock and reset
    logic clk;
    logic rst_n;
    
    // AXI Stream input interface
    logic        s_axis_rx_tvalid;
    logic        s_axis_rx_tready;
    logic [511:0] s_axis_rx_tdata;
    logic [63:0]  s_axis_rx_tkeep;
    logic        s_axis_rx_tlast;
    logic [15:0] s_axis_rx_tuser;
    
    // AXI Stream output interface  
    logic        m_axis_rx_tvalid;
    logic        m_axis_rx_tready;
    logic [511:0] m_axis_rx_tdata;
    logic [63:0]  m_axis_rx_tkeep;
    logic        m_axis_rx_tlast;
    logic [15:0] m_axis_rx_tuser;
    
    // Configuration interface (simplified)
    logic [31:0] cfg_data;
    logic [15:0] cfg_addr;
    logic        cfg_valid;
    logic        cfg_ready;
    
    // Status/debug signals
    logic        filter_drop_valid;
    logic [3:0]  filter_drop_reason;
    
    // Device Under Test
    filter_rx_pipeline #(
        .NUM_RULES(2)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        
        // Input AXI Stream
        .s_axis_rx_tvalid(s_axis_rx_tvalid),
        .s_axis_rx_tready(s_axis_rx_tready),
        .s_axis_rx_tdata(s_axis_rx_tdata),
        .s_axis_rx_tkeep(s_axis_rx_tkeep),
        .s_axis_rx_tlast(s_axis_rx_tlast),
        .s_axis_rx_tuser(s_axis_rx_tuser),
        
        // Output AXI Stream
        .m_axis_rx_tvalid(m_axis_rx_tvalid),
        .m_axis_rx_tready(m_axis_rx_tready),
        .m_axis_rx_tdata(m_axis_rx_tdata),
        .m_axis_rx_tkeep(m_axis_rx_tkeep),
        .m_axis_rx_tlast(m_axis_rx_tlast),
        .m_axis_rx_tuser(m_axis_rx_tuser)
        
        // Note: Configuration and status signals would be connected
        // based on the actual filter_rx_pipeline interface
    );
    
    // Connect debug/status signals if they exist in the actual module
    assign filter_drop_valid = 1'b0;  // Placeholder
    assign filter_drop_reason = 4'b0; // Placeholder
    
    // Initialize output ready
    initial begin
        m_axis_rx_tready = 1'b1;  // Always ready for output
    end
    
    // Dump waves for debugging
    initial begin
        $dumpfile("filter_rx_pipeline.vcd");
        $dumpvars(0, tb_filter_rx_pipeline);
    end

endmodule
