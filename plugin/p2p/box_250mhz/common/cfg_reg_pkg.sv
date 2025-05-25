// *************************************************************************
//
// Configuration Register Package
// Defines the configuration register structure for P2P filtering
//
// *************************************************************************

package cfg_reg_pkg;

    // Rule structure definition
    typedef struct packed {
        logic [31:0]  ipv4_addr;     // IPv4 address (32 bits)
        logic [127:0] ipv6_addr;     // IPv6 address (128 bits)
        logic [31:0]  port;          // Port number (32 bits)
    } rule_t;

    // Array of two rules
    typedef rule_t [1:0] rule_array_t;

    // Counters structure
    typedef struct packed {
        logic [31:0] rule0_hit_count;
        logic [31:0] rule1_hit_count;
        logic [31:0] total_packets;
        logic [31:0] dropped_packets;
    } counters_t;

    // Configuration register structure
    typedef struct packed {
        rule_array_t filter_rules;   // Array of filtering rules
        counters_t   counters;       // Packet counters
    } cfg_reg_t;

    // Constants
    parameter int NUM_RULES = 2;
    parameter int RULE_SIZE_BITS = $bits(rule_t);  // 192 bits per rule
    parameter int RULE_SIZE_WORDS = RULE_SIZE_BITS / 32;  // 6 words per rule

    // Register offsets for each rule field (word addresses)
    // Rule 0: 6 registers
    parameter int RULE0_IPV4_OFFSET    = 10'h000;
    parameter int RULE0_IPV6_0_OFFSET  = 10'h001;
    parameter int RULE0_IPV6_1_OFFSET  = 10'h002;
    parameter int RULE0_IPV6_2_OFFSET  = 10'h003;
    parameter int RULE0_IPV6_3_OFFSET  = 10'h004;
    parameter int RULE0_PORT_OFFSET    = 10'h005;

    // Rule 1: 6 registers
    parameter int RULE1_IPV4_OFFSET    = 10'h006;
    parameter int RULE1_IPV6_0_OFFSET  = 10'h007;
    parameter int RULE1_IPV6_1_OFFSET  = 10'h008;
    parameter int RULE1_IPV6_2_OFFSET  = 10'h009;
    parameter int RULE1_IPV6_3_OFFSET  = 10'h00A;
    parameter int RULE1_PORT_OFFSET    = 10'h00B;

endpackage
