#include "WireCellPcbro/RawSource.h"

#include "WireCellIface/ITensorSet.h"

#include "WireCellUtil/Testing.h"
#include "WireCellUtil/Array.h"
#include "WireCellUtil/Logging.h"

#include <sstream>

using spdlog::debug;
using spdlog::info;
using spdlog::error;



int main(int argc, char* argv[])
{
    WireCell::Log::add_stdout(true, "debug");
    // fixme, this shouldn't be needed to see debug level!
    spdlog::set_level(spdlog::level::debug); 

    if (argc != 2) {
        error("need a .bin file");
        return 0;
    }
    debug("starting");
    pcbro::RawSource rawsrc;

    auto cfg = rawsrc.default_configuration();
    cfg["filename"] = argv[1];
    cfg["tag"] = "test-tag";
    debug("cfg: {}", cfg);
    rawsrc.configure(cfg);
    
    WireCell::ITensorSet::pointer ts;
    while (true) {
        bool ok = rawsrc(ts);
        if (!ok) {
            debug("RawSource is empty");
            break;
        }
        if (!ts) {
            debug("RawSource sends EOS");
            continue;
        }
        debug("set metadata: {}", ts->metadata());
        auto tensors = ts->tensors();
        debug("{} tensors", tensors->size());
        for (auto& ten : *tensors) {
            debug("tensor metadata: {}", ten->metadata());
            auto shape = ten->shape();

            if (shape.size() == 1) {
                Eigen::Map<const Eigen::ArrayXi> arr((const int*) ten->data(), shape[0]);
                const auto& t = arr.transpose();
                std::stringstream ss;
                for (int ind=0; ind<10; ++ind) {
                    ss << " " << t(ind);
                }
                debug(ss.str());
            }
            if (shape.size() == 2) {
                Eigen::Map<const Eigen::ArrayXXf> arr((const float*) ten->data(), shape[0], shape[1]);
                for (int row=0; row<10; ++row) {
                    std::stringstream ss;
                    for (int col=0; col<10; ++col) {
                        float x = arr(row,col);
                        ss << fmt::format(" {:.0f}", x);
                    }
                    debug(ss.str());
                }
            }
        }
    }
    // add more tests, use Assert().
    return 0;
}
