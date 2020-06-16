// write lots and lots and lots and lots of tests

#include "WireCellPcbro/RawSource.h"
#include "WireCellUtil/Testing.h"

#include <iostream>

int main()
{
    pcbro::RawSource obj;
    auto cfg = obj.default_configuration();
    std::cout << cfg << std::endl;
    obj.configure(cfg);
    
    // add more tests, use Assert().
    return 0;
}