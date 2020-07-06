#include "WireCellPcbro/BinFile.h"
#include "WireCellUtil/Logging.h"

#include <iterator>

using spdlog::debug;
using spdlog::info;
using spdlog::error;

int test_read(std::istream& stream)
{
    pcbro::raw_data_t rd = pcbro::read_raw_data(stream);
    info("read: {} shorts, first cnt: {}",
         rd.size(), pcbro::word(rd.begin()));
    return 0;
}

int test_package(std::istream& stream)
{
    pcbro::raw_data_t rd = pcbro::read_raw_data(stream);
    pcbro::raw_data_itr beg = rd.begin();
    int npkg = 0;
    while (true) {
        pcbro::raw_data_itr end = pcbro::seek_package(beg, rd.end());
            
        info("package {:2d}: size: {}", npkg, std::distance(beg, end));
        int count = 0;
        auto it = beg;
        while (count < 10) {
            const uint16_t s = *it;
            info("{:2d} 0x{:04x} {:d}", count, s, s);
            ++it;
            ++count;
        }
        ++npkg;
        if (end == rd.end()) {
            break;
        }
        beg = end;
    }
    return 0;
}

int test_link(std::istream& stream)
{
    pcbro::raw_data_t rd = pcbro::read_raw_data(stream);
    pcbro::link_data_t ld;
    pcbro::raw_data_itr next = pcbro::make_link(rd.begin(), rd.end(), 
                                                pcbro::link_data_bitr(ld));
    assert(next != rd.end());
    info("link: consumed raw: {}, made link: {}",
         std::distance(rd.begin(), next), ld.size());
    return 0;
}

int test_trigger(std::istream& stream)
{
    pcbro::raw_data_t rd = pcbro::read_raw_data(stream);
    pcbro::block128_t block;
    pcbro::make_trigger(block, rd.begin(), rd.end());
    info("trigger has {} ticks, sum={}, avg={}",
         block.rows(), block.sum(),
         block.sum()/(1.0*block.rows()*block.cols()));    
    for (int ind = 0; ind < 128; ind += 16) {
        info("corner {}:\n{}" , ind, block.block(0,0,16,10));
    }

    return 0;
}

int test_file(std::istream& stream)
{
    pcbro::raw_data_t rd = pcbro::read_raw_data(stream);
    pcbro::raw_data_itr beg = rd.begin();
    while (true) {
        pcbro::block128_t block;
        beg = pcbro::make_trigger(block, beg, rd.end());
        info("trigger has {} ticks", block.rows());
    }
    return 0;
}

int main(int argc, char* argv[])
{
    if (argc != 3) {
        return 0;
    }
    WireCell::Log::add_stdout(true, "debug");
    std::string test=argv[1];
    auto fpd = pcbro::parse_file_path(argv[2]);
    info("fpd: {} {} {} {}.{:03d} {}", 
         fpd.wibnn, fpd.stepnn, fpd.fembnn,
         fpd.seconds, fpd.msecs, fpd.path);

    std::ifstream fstr(argv[2]);
    if (!fstr) {
        throw std::runtime_error("bad file");
    }
    info("bin file {} with {}", argv[1], argv[2]);

    if (test=="read") {
        return test_read(fstr);
    }
    if (test=="package") {
        return test_package(fstr);
    }
    if (test == "link") {
        return test_link(fstr);
    }
    if (test == "trigger") {
        return test_trigger(fstr);
    }
    if (test == "file") {
        return test_file(fstr);
    }
    error("unknown test: {}", test);
    return 0;

}
