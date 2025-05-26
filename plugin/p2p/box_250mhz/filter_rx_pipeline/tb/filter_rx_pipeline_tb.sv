// *************************************************************************
//
// Enhanced Testbench for filter_rx_pipeline with comprehensive testing
// Designed to work with multiple simulators (iverilog, modelsim, etc.)
//
// *************************************************************************

`timescale 1ns / 1ps

import cfg_reg_pkg::*;
import packet_pkg::*;

module filter_rx_pipeline_tb;

    // Clock and Reset
    reg        aclk = 0;
    reg        aresetn = 0;

    // Slave AXI Stream Interface (from adapter)
    wire        s_axis_tvalid;
    wire [511:0] s_axis_tdata;
    wire [63:0]  s_axis_tkeep;
    wire        s_axis_tlast;
    wire [47:0] s_axis_tuser;
    wire        s_axis_tready;

    // Master AXI Stream Interface (to QDMA)
    wire        m_axis_tvalid;
    wire [511:0] m_axis_tdata;
    wire [63:0]  m_axis_tkeep;
    wire        m_axis_tlast;
    wire [47:0] m_axis_tuser;
    reg         m_axis_tready = 1;

    // Configuration register inputs
    reg [31:0]  cfg_reg_filter_rules_0_ipv4_addr = 0;
    reg [127:0] cfg_reg_filter_rules_0_ipv6_addr = 0;
    reg [31:0]  cfg_reg_filter_rules_0_port = 0;
    reg [31:0]  cfg_reg_filter_rules_1_ipv4_addr = 0;
    reg [127:0] cfg_reg_filter_rules_1_ipv6_addr = 0;
    reg [31:0]  cfg_reg_filter_rules_1_port = 0;

    // Counter outputs (from DUT)
    wire [31:0]  rule0_hit_count;
    wire [31:0]  rule1_hit_count;
    wire [31:0]  total_packets;
    wire [31:0]  dropped_packets;

    // Pack configuration register structure
    cfg_reg_t cfg_reg_in;
    status_reg_t status_reg_out;
    
    assign cfg_reg_in.filter_rules[0].ipv4_addr = cfg_reg_filter_rules_0_ipv4_addr;
    assign cfg_reg_in.filter_rules[0].ipv6_addr = cfg_reg_filter_rules_0_ipv6_addr;
    assign cfg_reg_in.filter_rules[0].port = cfg_reg_filter_rules_0_port;
    assign cfg_reg_in.filter_rules[1].ipv4_addr = cfg_reg_filter_rules_1_ipv4_addr;
    assign cfg_reg_in.filter_rules[1].ipv6_addr = cfg_reg_filter_rules_1_ipv6_addr;
    assign cfg_reg_in.filter_rules[1].port = cfg_reg_filter_rules_1_port;
    
    // Extract status outputs from DUT
    assign rule0_hit_count = status_reg_out.rule0_hit_count;
    assign rule1_hit_count = status_reg_out.rule1_hit_count;
    assign total_packets = status_reg_out.total_packets;
    assign dropped_packets = status_reg_out.dropped_packets;

    // Packet generator signals
    reg        pkt_gen_enable = 0;
    reg [31:0] pkt_gen_src_ip = 32'h00000000;
    reg [31:0] pkt_gen_dst_ip = 32'h00000000;
    reg [15:0] pkt_gen_src_port = 16'h0000;
    reg [15:0] pkt_gen_dst_port = 16'h0000;
    reg [15:0] pkt_gen_length = 16'd64;
    reg        pkt_gen_ipv6 = 0;
    reg [127:0] pkt_gen_src_ipv6 = 128'h0;
    reg [127:0] pkt_gen_dst_ipv6 = 128'h0;
    
    // Scoreboard signals
    reg [31:0] expected_rule0_hits = 0;
    reg [31:0] expected_rule1_hits = 0;
    reg [31:0] expected_total_packets = 0;
    reg [31:0] expected_dropped_packets = 0;
    
    // Performance counters
    reg [63:0] test_start_time = 0;
    reg [63:0] test_end_time = 0;
    reg [31:0] packets_sent = 0;
    reg [31:0] packets_received = 0;
    
    // Test status
    reg test_running = 0;
    reg [31:0] current_test = 0;
    
    // Clock generation
    always #2.5 aclk = ~aclk; // 200MHz clock

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
        .status_reg(status_reg_out),
        
        .aclk(aclk),
        .aresetn(aresetn)
    );

    // Packet Generator Module
    packet_generator pkt_gen (
        .clk(aclk),
        .reset_n(aresetn),
        .enable(pkt_gen_enable),
        .src_ip(pkt_gen_src_ip),
        .dst_ip(pkt_gen_dst_ip),
        .src_port(pkt_gen_src_port),
        .dst_port(pkt_gen_dst_port),
        .packet_length(pkt_gen_length),
        .ipv6_mode(pkt_gen_ipv6),
        .src_ipv6(pkt_gen_src_ipv6),
        .dst_ipv6(pkt_gen_dst_ipv6),
        .m_axis_tvalid(s_axis_tvalid),
        .m_axis_tdata(s_axis_tdata),
        .m_axis_tkeep(s_axis_tkeep),
        .m_axis_tlast(s_axis_tlast),
        .m_axis_tuser(s_axis_tuser),
        .m_axis_tready(s_axis_tready)
    );
    
    // Packet Sink Module
    packet_sink pkt_sink (
        .clk(aclk),
        .reset_n(aresetn),
        .s_axis_tvalid(m_axis_tvalid),
        .s_axis_tdata(m_axis_tdata),
        .s_axis_tkeep(m_axis_tkeep),
        .s_axis_tlast(m_axis_tlast),
        .s_axis_tuser(m_axis_tuser),
        .s_axis_tready(m_axis_tready),
        .packets_received(packets_received)
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

    // Simplified Test Tasks (compatible with more simulators)
    task reset_system;
        begin
            aresetn = 0;
            pkt_gen_enable = 0;
            #50; // Use delay instead of repeat(@posedge)
            aresetn = 1;
            #25;
            $display("[%0t] System reset complete", $time);
        end
    endtask
    
    task configure_filter_rules;
        input [31:0] rule0_ipv4, rule1_ipv4;
        input [15:0] rule0_port, rule1_port;
        input [127:0] rule0_ipv6, rule1_ipv6;
        begin
            cfg_reg_filter_rules_0_ipv4_addr = rule0_ipv4;
            cfg_reg_filter_rules_0_port = {16'h0, rule0_port};
            cfg_reg_filter_rules_0_ipv6_addr = rule0_ipv6;
            cfg_reg_filter_rules_1_ipv4_addr = rule1_ipv4;
            cfg_reg_filter_rules_1_port = {16'h0, rule1_port};
            cfg_reg_filter_rules_1_ipv6_addr = rule1_ipv6;
            #5; // Simple delay
            $display("[%0t] Filter rules configured", $time);
        end
    endtask
    
    task send_ipv4_packet;
        input [31:0] src_ip, dst_ip;
        input [15:0] src_port, dst_port;
        input [15:0] length;
        begin
            $display("[%0t] Sending IPv4 packet: %d.%d.%d.%d:%d -> %d.%d.%d.%d:%d", 
                     $time,
                     src_ip[31:24], src_ip[23:16], src_ip[15:8], src_ip[7:0], src_port,
                     dst_ip[31:24], dst_ip[23:16], dst_ip[15:8], dst_ip[7:0], dst_port);
            pkt_gen_src_ip = src_ip;
            pkt_gen_dst_ip = dst_ip;
            pkt_gen_src_port = src_port;
            pkt_gen_dst_port = dst_port;
            pkt_gen_length = length;
            pkt_gen_ipv6 = 0;
            pkt_gen_enable = 1;
            #5;
            pkt_gen_enable = 0;
            packets_sent = packets_sent + 1;
            #500; // Wait for packet processing
            $display("[%0t] Packet processing complete. Packets received by sink: %0d", $time, packets_received);
        end
    endtask
    
    task send_ipv6_packet;
        input [127:0] src_ipv6, dst_ipv6;
        input [15:0] src_port, dst_port;
        input [15:0] length;
        begin
            $display("[%0t] Sending IPv6 packet: %04x:%04x:...:%04x:%d -> %04x:%04x:...:%04x:%d", 
                     $time,
                     src_ipv6[127:112], src_ipv6[111:96], src_ipv6[15:0], src_port,
                     dst_ipv6[127:112], dst_ipv6[111:96], dst_ipv6[15:0], dst_port);
            pkt_gen_src_ipv6 = src_ipv6;
            pkt_gen_dst_ipv6 = dst_ipv6;
            pkt_gen_src_port = src_port;
            pkt_gen_dst_port = dst_port;
            pkt_gen_length = length;
            pkt_gen_ipv6 = 1;
            pkt_gen_enable = 1;
            #5;
            pkt_gen_enable = 0;
            packets_sent = packets_sent + 1;
            #500; // Wait for packet processing
            $display("[%0t] Packet processing complete. Packets received by sink: %0d", $time, packets_received);
        end
    endtask
    
    task check_counters;
        begin
            $display("[%0t] Counter Check:", $time);
            $display("  Rule 0 hits: %0d (expected %0d)", rule0_hit_count, expected_rule0_hits);
            $display("  Rule 1 hits: %0d (expected %0d)", rule1_hit_count, expected_rule1_hits);
            $display("  Total packets: %0d (expected %0d)", total_packets, expected_total_packets);
            $display("  Dropped packets: %0d (expected %0d)", dropped_packets, expected_dropped_packets);
            $display("  Packets sent: %0d, Packets received: %0d", packets_sent, packets_received);
            
            if (rule0_hit_count != expected_rule0_hits ||
                rule1_hit_count != expected_rule1_hits ||
                total_packets != expected_total_packets ||
                dropped_packets != expected_dropped_packets) begin
                $error("Counter mismatch detected!");
            end else begin
                $display("  All counters match expected values ✓");
            end
            
            // Check packet flow consistency
            if (packets_received != (packets_sent - dropped_packets)) begin
                $error("Packet flow mismatch: sent=%0d, received=%0d, dropped=%0d", 
                       packets_sent, packets_received, dropped_packets);
            end else begin
                $display("  Packet flow consistency check passed ✓");
            end
        end
    endtask
    
    task report_throughput;
        input [63:0] cycles;
        input [31:0] packets;
        real throughput_pps, throughput_gbps;
        begin
            throughput_pps = (packets * 200_000_000.0) / cycles;
            throughput_gbps = (packets * 64 * 8 * 200_000_000.0) / (cycles * 1_000_000_000.0);
            $display("[%0t] Throughput Report:", $time);
            $display("  Cycles: %0d", cycles);
            $display("  Packets: %0d", packets);
            $display("  Throughput: %.2f packets/sec", throughput_pps);
            $display("  Throughput: %.2f Gbps (64-byte packets)", throughput_gbps);
        end
    endtask

    // Add debug monitoring
    always @(posedge aclk) begin
        if (aresetn) begin
            if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
                $display("[%0t] Packet entered DUT (from generator)", $time);
            end
            if (m_axis_tvalid && m_axis_tready && m_axis_tlast) begin
                $display("[%0t] Packet exited DUT (to sink)", $time);
            end
            
            // Monitor filter decisions
            if (p1_tvalid) begin
                $display("[%0t] Filter decision: pass=%b, rule_hit=%b", $time, p1_filter_pass, p1_rule_hit);
            end
        end
    end
    
    // Monitor counter changes
    reg [31:0] prev_rule0_hits = 0;
    reg [31:0] prev_rule1_hits = 0;
    reg [31:0] prev_total_packets = 0;
    reg [31:0] prev_dropped_packets = 0;
    
    always @(posedge aclk) begin
        if (aresetn) begin
            if (rule0_hit_count != prev_rule0_hits) begin
                $display("[%0t] Rule 0 hit count: %0d -> %0d", $time, prev_rule0_hits, rule0_hit_count);
                prev_rule0_hits = rule0_hit_count;
            end
            if (rule1_hit_count != prev_rule1_hits) begin
                $display("[%0t] Rule 1 hit count: %0d -> %0d", $time, prev_rule1_hits, rule1_hit_count);
                prev_rule1_hits = rule1_hit_count;
            end
            if (total_packets != prev_total_packets) begin
                $display("[%0t] Total packets: %0d -> %0d", $time, prev_total_packets, total_packets);
                prev_total_packets = total_packets;
            end
            if (dropped_packets != prev_dropped_packets) begin
                $display("[%0t] Dropped packets: %0d -> %0d", $time, prev_dropped_packets, dropped_packets);
                prev_dropped_packets = dropped_packets;
            end
        end
    end

    // Test Scenarios
    initial begin
        $display("Starting filter_rx_pipeline comprehensive testbench");
        
        // Initialize
        reset_system();
        
        // Test 1: Basic IPv4 Rule Matching
        $display("\n=== Test 1: Basic IPv4 Rule Matching ===");
        current_test = 1;
        configure_filter_rules(
            32'hC0A80101, 32'hC0A80102,  // 192.168.1.1, 192.168.1.2
            16'h1F90, 16'h2382,         // 8080, 9090
            128'h0, 128'h0
        );
        
        // Reset packet counters for this test
        packets_sent = 0;
        packets_received = 0;
        expected_rule0_hits = 0;
        expected_rule1_hits = 0;
        expected_total_packets = 0;
        expected_dropped_packets = 0;
        
        // Send packets matching Rule 0 (IP: 192.168.1.1, Port: 8080)
        $display("--- Sending packets matching Rule 0 ---");
        expected_rule0_hits = 1;
        expected_total_packets = 1;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80101, 16'h2710, 16'h1F90, 16'd64);
        check_counters();
        
        expected_rule0_hits = 2;
        expected_total_packets = 2;
        send_ipv4_packet(32'hC0A80005, 32'hC0A80101, 16'h3039, 16'h1F90, 16'd128);
        check_counters();
        
        // Send packets matching Rule 1 (IP: 192.168.1.2, Port: 9090)
        $display("--- Sending packets matching Rule 1 ---");
        expected_rule1_hits = 1;
        expected_total_packets = 3;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80102, 16'h2710, 16'h2382, 16'd64);
        check_counters();
        
        expected_rule1_hits = 2;
        expected_total_packets = 4;
        send_ipv4_packet(32'hC0A80010, 32'hC0A80102, 16'h4E20, 16'h2382, 16'd256);
        check_counters();
        
        // Send non-matching packets (should be dropped)
        $display("--- Sending non-matching packets ---");
        expected_dropped_packets = 1;
        expected_total_packets = 5;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80103, 16'h2710, 16'h50, 16'd64);
        check_counters();
        
        expected_dropped_packets = 2;
        expected_total_packets = 6;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80101, 16'h2710, 16'h51, 16'd64);  // Wrong port
        check_counters();
        
        // Test 2: IPv6 Rule Matching
        $display("\n=== Test 2: IPv6 Rule Matching ===");
        current_test = 2;
        reset_system();
        configure_filter_rules(
            32'h0, 32'h0,  // No IPv4 rules
            16'h0, 16'h0,
            128'h20010db8000000000000000000000001,  // 2001:db8::1
            128'h20010db8000000000000000000000002   // 2001:db8::2
        );
        
        // Reset packet counters for this test
        packets_sent = 0;
        packets_received = 0;
        expected_rule0_hits = 0;
        expected_rule1_hits = 0;
        expected_total_packets = 0;
        expected_dropped_packets = 0;
        
        // Send IPv6 packets matching rules
        $display("--- Sending IPv6 packets matching Rule 0 ---");
        expected_rule0_hits = 1;
        expected_total_packets = 1;
        send_ipv6_packet(128'h20010db8000000000000000000000010, 128'h20010db8000000000000000000000001, 
                        16'h2710, 16'h1F90, 16'd64);
        check_counters();
        
        $display("--- Sending IPv6 packets matching Rule 1 ---");
        expected_rule1_hits = 1;
        expected_total_packets = 2;
        send_ipv6_packet(128'h20010db8000000000000000000000020, 128'h20010db8000000000000000000000002, 
                        16'h2710, 16'h2382, 16'd64);
        check_counters();
        
        // Test 3: Mixed IPv4 and IPv6 Traffic
        $display("\n=== Test 3: Mixed IPv4 and IPv6 Traffic ===");
        current_test = 3;
        reset_system();
        configure_filter_rules(
            32'hC0A80101, 32'hC0A80102,
            16'h1F90, 16'h2382,
            128'h20010db8000000000000000000000001,
            128'h20010db8000000000000000000000002
        );
        
        // Reset packet counters for this test
        packets_sent = 0;
        packets_received = 0;
        expected_rule0_hits = 0;
        expected_rule1_hits = 0;
        expected_total_packets = 0;
        expected_dropped_packets = 0;
        
        // Interleaved IPv4 and IPv6 packets
        $display("--- Sending mixed IPv4/IPv6 traffic ---");
        expected_rule0_hits = 1;
        expected_total_packets = 1;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80101, 16'h2710, 16'h1F90, 16'd64);
        check_counters();
        
        expected_rule0_hits = 2;
        expected_total_packets = 2;
        send_ipv6_packet(128'h20010db8000000000000000000000010, 128'h20010db8000000000000000000000001, 
                        16'h2710, 16'h1F90, 16'd64);
        check_counters();
        
        expected_rule1_hits = 1;
        expected_total_packets = 3;
        send_ipv4_packet(32'hC0A80001, 32'hC0A80102, 16'h2710, 16'h2382, 16'd64);
        check_counters();
        
        expected_rule1_hits = 2;
        expected_total_packets = 4;
        send_ipv6_packet(128'h20010db8000000000000000000000020, 128'h20010db8000000000000000000000002, 
                        16'h2710, 16'h2382, 16'd64);
        check_counters();
        
        // Test 4: Performance Test with Matching Packets
        $display("\n=== Test 4: Performance Test with Matching Packets ===");
        current_test = 4;
        reset_system();
        configure_filter_rules(
            32'hC0A80101, 32'hC0A80102,
            16'h1F90, 16'h2382,
            128'h0, 128'h0
        );
        
        // Reset packet counters for this test
        packets_sent = 0;
        packets_received = 0;
        expected_rule0_hits = 0;
        expected_rule1_hits = 0;
        expected_total_packets = 0;
        expected_dropped_packets = 0;
        
        test_start_time = $time;
        for (int i = 0; i < 10; i++) begin
            if (i % 2 == 0) begin
                expected_rule0_hits = expected_rule0_hits + 1;
                send_ipv4_packet(32'hC0A80001, 32'hC0A80101, 16'h2710, 16'h1F90, 16'd64);
            end else begin
                expected_rule1_hits = expected_rule1_hits + 1;
                send_ipv4_packet(32'hC0A80001, 32'hC0A80102, 16'h2710, 16'h2382, 16'd64);
            end
            expected_total_packets = expected_total_packets + 1;
        end
        test_end_time = $time;
        
        check_counters();
        report_throughput(test_end_time - test_start_time, 10);
        
        // Test 5: Edge Cases and Error Conditions
        $display("\n=== Test 5: Edge Cases ===");
        current_test = 5;
        reset_system();
        configure_filter_rules(
            32'hFFFFFFFF, 32'h00000000,  // Broadcast and null IP
            16'hFFFF, 16'h0000,         // Max and min ports
            128'h0, 128'h0
        );
        
        // Reset packet counters for this test
        packets_sent = 0;
        packets_received = 0;
        expected_rule0_hits = 0;
        expected_rule1_hits = 0;
        expected_total_packets = 0;
        expected_dropped_packets = 0;
        
        // Test edge case IPs and ports
        $display("--- Testing edge case values ---");
        expected_rule0_hits = 1;
        expected_total_packets = 1;
        send_ipv4_packet(32'hC0A80001, 32'hFFFFFFFF, 16'h2710, 16'hFFFF, 16'd64);
        check_counters();
        
        expected_rule1_hits = 1;
        expected_total_packets = 2;
        send_ipv4_packet(32'hC0A80001, 32'h00000000, 16'h2710, 16'h0000, 16'd64);
        check_counters();
        
        $display("\n=== All Tests Complete ===");
        $display("Final Statistics:");
        $display("  Total packets sent: %0d", packets_sent);
        $display("  Total packets received: %0d", packets_received);
        $display("  Rule 0 hits: %0d", rule0_hit_count);
        $display("  Rule 1 hits: %0d", rule1_hit_count);
        $display("  Total packets processed: %0d", total_packets);
        $display("  Dropped packets: %0d", dropped_packets);
        $display("Total simulation time: %0t", $time);
        $finish;
    end

    // Simulation timeout
    initial begin
        #100000; // 100us timeout
        $display("ERROR: Simulation timeout!");
        $finish;
    end

endmodule
