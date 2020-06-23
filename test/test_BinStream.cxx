#include "WireCellPcbro/BinStream.h"

#include <iostream>
#include <fstream>

void dump_shorts(std::string fname)
{
    std::cout << "shorts:\n";
    std::ifstream fstr(fname);
    for (int ind=0; ind<10; ++ind) {
        uint16_t i = pcbro::read_short(fstr);
        std::cout << std::dec << ind << " " << i << " " << std::hex << i << std::endl;
    }
    std::cout << "^^^" << std::endl;
}

void dump_ints(std::string fname)
{
    std::cout << "ints:\n";
    std::ifstream fstr(fname);
    for (int ind=0; ind<5; ++ind) {
        uint32_t i = pcbro::read_int(fstr);
        std::cout << std::dec << ind << " " << i << " " << std::hex << i << std::endl;
    }
    std::cout << "^^^" << std::endl;
}

void dump(pcbro::Header& h)
{
    std::cout << "Main: header: seq:" << std::dec << h.seq
              << " res:" << h.res
              << " cont:" << std::hex << h.cont << std::endl;
}

int test_package_level(std::istream& fstr)
{

    const size_t max_shorts = 0x1df4/2; // 3834
    const size_t max_rows = (max_shorts - 9) / 25; // 153

    size_t count=0;
    size_t nrows=0;
    size_t nlinks = 0;

    pcbro::block32_t block;
    while (true) {

        pcbro::Header nhead;
        try {
            nhead = pcbro::read_package(fstr, block);
        }
        catch (const std::range_error& e) {
            std::cerr << e.what() << "\nbailing from package level\n";
            break;
        }
        dump(nhead);

        const size_t drows = block.rows() - nrows;
        
        std::cerr << "Main: " << std::dec << " pkg:"<< count
                  << " totrows:" << block.rows()
                  << " newrows:" << drows
                  << std::endl;
        for (int irow=nrows; irow < block.rows(); ++irow) {
            std::cerr << "row: " << irow;
            for (int ind=0; ind<32; ++ind) {
                uint16_t sample = block(irow,ind);
                std::cerr << " " << ind << ":" << sample;
                if (sample & 0xf000) {
                    std::cerr << std::endl;
                    assert((sample & 0xf000) == 0);
                }
            }            
            std::cerr << std::endl;
        }

    
        nrows = block.rows();
        ++count;
        if (drows < max_rows) {
            std::cerr << "Main: clearing link " << nlinks << " after " << nrows << "!\n";
            ++nlinks;
            count=nrows=0;
            block.resize(0, Eigen::NoChange);
        }

    }
    return 0;
}


int test_link_level(std::istream& fstr)
{
    pcbro::block32_t block;
    int nlinks = 0;
    bool keep_going = true;
    while (keep_going) {
        try {
            pcbro::read_link(fstr, block);
        }
        catch (const std::range_error& e) {
            std::cerr << e.what() << std::endl;
            std::cerr << "bailing from link level" << std::endl;
            keep_going = false;
        }
        std::cerr << "Main: " << std::dec << " link:"<< nlinks
                  << " totrows:" << block.rows()
                  << " keep_going:" << keep_going
                  << std::endl;
        ++nlinks;
    }
    return 0;
}

int test_trigger_level(std::istream& fstr)
{
    pcbro::block128_t trigger;
    size_t ntrigs=0;
    bool keep_going = true;
    while (keep_going) {
        try {
            pcbro::read_trigger(fstr, trigger);
        }
        catch (const std::range_error& e) {
            std::cerr << e.what() << std::endl;
            std::cerr << "bailing from trigger level" << std::endl;
            keep_going = false;
        }
        std::cerr << "Main: " << std::dec << " trigger:"<< ntrigs
                  << " rXc:" << trigger.rows() << "," << trigger.cols()
                  << " min:" << trigger.minCoeff()
                  << " max:" << trigger.maxCoeff()
                  << " tot:" << trigger.sum()
                  << " avg:" << trigger.sum()/(1.0*trigger.rows()*trigger.cols())
                  << std::endl;
        for (int ich=0; ich<128; ++ich) {
            std::cerr << " " << ich << ":" << trigger.col(ich).sum()/(1.0*trigger.rows());
        }
        std::cerr << std::endl;
        ++ntrigs;
        trigger.resize(0, Eigen::NoChange);
    }
    return 0;
}

int main(int argc, char* argv[])
{
    if (argc != 3) {
        return 0;
    }
    std::string test=argv[1];
    std::ifstream fstr(argv[2]);
    if (!fstr) {
        throw std::runtime_error("bad file");
    }

    // prime the pump.  fixme: this should probably be absorbed in BinSream somehow.
    pcbro::Header header;
    fstr >> header;
    dump(header);

    if (test=="package") {
        return test_package_level(fstr);
    }
    if (test == "link") {
        return test_link_level(fstr);
    }
    if (test == "trigger") {
        return test_trigger_level(fstr);
    }
    std::cerr << "unknown test: " << test << std::endl;
    return 0;
}
