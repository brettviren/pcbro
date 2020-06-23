#include "WireCellPcbro/RawSource.h"
#include "WireCellUtil/Testing.h"
#include "WireCellUtil/Array.h"
#include "WireCellIface/ITensorSet.h"

#include <iostream>

int main(int argc, char* argv[])
{
    if (argc != 2) {
        std::cerr << "need a .bin file" << std::endl;
        return 0;
    }

    pcbro::RawSource rawsrc;

    auto cfg = rawsrc.default_configuration();
    cfg["filename"] = argv[1];
    cfg["tag"] = "test-tag";
    std::cout << cfg << std::endl;
    rawsrc.configure(cfg);
    
    WireCell::ITensorSet::pointer ts;
    while (true) {
        bool ok = rawsrc(ts);
        if (!ok) {
            std::cerr << "RawSource is empty\n";
            break;
        }
        if (!ts) {
            std::cerr << "RawSource sends EOS\n";
            continue;
        }
        std::cerr << "set metadata: " << ts->metadata() << std::endl;
        auto tensors = ts->tensors();
        std::cerr << tensors->size() << " tensors\n";
        for (auto& ten : *tensors) {
            std::cerr << "tensor metadata: " << ten->metadata() << std::endl;
            auto shape = ten->shape();
            std::cerr << "shape:";
            for (auto s : shape) {
                std::cerr << " " << s;
            }
            std::cerr << std::endl;
            if (shape.size() == 1) {
                Eigen::Map<const Eigen::ArrayXi> arr((const int*) ten->data(), shape[0]);
                const auto& t = arr.transpose();
                for (int ind=0; ind<10; ++ind) {
                    std::cerr << " " << t(ind);
                }
                std::cerr << std::endl;
            }
            if (shape.size() == 2) {
                Eigen::Map<const Eigen::ArrayXXf> arr((const float*) ten->data(), shape[0], shape[1]);
                for (int row=0; row<10; ++row) {
                    for (int col=0; col<10; ++col) {
                        std::cerr << " " << arr(row,col);
                    }
                    std::cerr << std::endl;
                }
            }
        }
    }
    // add more tests, use Assert().
    return 0;
}
