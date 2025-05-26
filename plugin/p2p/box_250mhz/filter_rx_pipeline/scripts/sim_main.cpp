#include <verilated.h>
#include "Vfilter_rx_pipeline_tb.h"
#include <iostream>

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    
    Vfilter_rx_pipeline_tb* tb = new Vfilter_rx_pipeline_tb;
    
    // Run for enough time to complete the test
    for (int i = 0; i < 200000 && !Verilated::gotFinish(); i++) {
        tb->eval();
    }
    
    delete tb;
    return 0;
}
