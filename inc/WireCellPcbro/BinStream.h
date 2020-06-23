// Access to a pcbro binary stream.

#ifndef PCBRO_BINSTREAM_H_SEEN
#define PCBRO_BINSTREAM_H_SEEN

#include <Eigen/Core>

#include <iostream>
#include <istream>
#include <vector>

namespace pcbro {

    // Many N samples (rows) across 32 contiguous channels (columns).
    using block32_t = Eigen::Array<uint16_t, Eigen::Dynamic, 32>;
    using block128_t = Eigen::Array<uint16_t, Eigen::Dynamic, 128>;


    inline uint32_t toint(char* dat) {
        return 0xffffffff & ((0xff&dat[0]) << 24 | (0xff&dat[1]) << 16 | (0xff&dat[2]) << 8 | (0xff&dat[1]));
    }
    inline uint32_t toint(uint16_t first, uint16_t second) {
        return 0xffffffff & ((0xffff&first)<<16 | (0xffff&second));
    }

    inline uint32_t read_int(std::istream& s) {
        char buf[4];
        s.read(buf, 4);
        return 0xffffffff & ((0xff&buf[0]) << 24 | (0xff&buf[1]) << 16 | (0xff&buf[2]) << 8 | (0xff&buf[3]));
    }
    inline uint16_t read_short(std::istream& s) {
        char buf[2];
        s.read(buf, 2);
        //std::cerr << "short: " << std::hex << (int)buf[0] << " " << (int)buf[1] << std::endl;
        return 0xffff&(((0xff & buf[0]) <<8) | (0xff & buf[1]));
    }
    inline void read_nshorts(std::istream& s, size_t n, uint16_t buf[]) {
        for (size_t ind=0; ind<n; ++n) {
            buf[ind] = read_short(s);
        }
    }

    // A header is the first 9 shorts which this fills out to 5 bytes
    struct Header {
        // first word (2 shorts) is a packet count
        uint32_t seq{0};
        // second word should always be zero
        uint32_t res{0};
        // next four shorts are unknown and seem constant across all
        // headers in a file.  Last one is zero.
        uint16_t u0{0}, u1{0}, u2{0}, u3{0};

        // The previous package 
        // last one appears to be a "continuation" value.  First
        // header has this zero then four with it non-zero values
        // always near to 0xf000 but with no obvious pattern
        uint16_t cont{0};
        // Do not use this.
        uint16_t padding{0};
    };
    std::istream& operator>>(std::istream& in, Header& h) {
        h.seq = read_int(in);
        h.res = read_int(in);
        h.u0 = read_short(in);
        h.u1 = read_short(in);
        h.u2 = read_short(in);
        h.u3 = read_short(in);
        h.cont = read_short(in);
        h.padding = 0;
        return in;
    }


    // Often the stream must discover the start of a header so we want
    // a way to to stream the remainer
    struct PartialHeader : public Header{
        PartialHeader(uint32_t num) {
            seq = num;
        }
    };
    std::istream& operator>>(std::istream& in, PartialHeader& h) {
        // already have seq.
        h.res = read_int(in);
        h.u0 = read_short(in);
        h.u1 = read_short(in);
        h.u2 = read_short(in);
        h.u3 = read_short(in);
        h.cont = read_short(in);
        h.padding = 0;
        return in;
    }

    inline Eigen::Index fill4(block32_t& block, Eigen::Index irow, Eigen::Index icol, char* buf) {
        block(irow, icol+3) = 0x0fff&((0x0f00&(buf[1]<<8))|(0xff&(buf[0]<<0)));
        block(irow, icol+2) = 0x0fff&((0x0ff0&(buf[2]<<4))|(0x0f&(buf[1]>>4)));

        block(irow, icol+1) = 0x0fff&((0x0f00&(buf[4]<<8))|(0xff&(buf[3]<<0)));
        block(irow, icol+0) = 0x0fff&((0x0ff0&(buf[5]<<4))|(0x0f&(buf[4]>>4)));

        return icol+4;
    };

    inline void append_sample(char buf[], block32_t& block) {
        Eigen::Index irow = block.rows();
        block.resize(irow+1, Eigen::NoChange);

        // std::cerr << "appending: " << irow << std::endl;
        // for (int ind=0; ind<48; ++ind) {
        //     std::cerr << std::hex << " " << (int)(0xff&buf[ind]);
        // }
        // std::cerr << std::endl;

        Eigen::Index icol = 0;
        
        icol = fill4(block, irow, icol, &buf[6]);
        icol = fill4(block, irow, icol, &buf[0]);
        
        icol = fill4(block, irow, icol, &buf[18]);
        icol = fill4(block, irow, icol, &buf[12]);

        icol = fill4(block, irow, icol, &buf[30]);
        icol = fill4(block, irow, icol, &buf[24]);
        
        icol = fill4(block, irow, icol, &buf[42]);
        icol = fill4(block, irow, icol, &buf[36]);

        assert(icol == 32);
        for (int ind=0; ind<icol; ++ind) {
            uint16_t sample = block(irow, ind);
            assert((sample&0xf000) == 0);
            //std::cerr << std::hex << " " << block(irow,ind);
        }
        //std::cerr << std::endl;
    }
    
    /// Read in and append one package of samples to a block.  Reading
    /// continues until a non-sample marker is found.  This is assumed
    /// to start a new header, which is read in and returned.
    inline Header read_package(std::istream& in, block32_t& block, size_t max_rows = 153) {
        char buf[48];
        uint16_t first = read_short(in);
        size_t nrows = 0;
        while (first == 0xface or first == 0xfeed) {
            ++nrows;
            if (nrows > max_rows) {
                // It seems the DAQ can start saving without breaking
                // up data into packages.
                throw std::range_error("exceed max row");
            }
            in.read(buf, 48);    // one sample

            uint16_t second = read_short(in); // either face/feed or seq.
            if (second == 0xface or second == 0xfeed) {
                append_sample(buf, block);
                first = second;
                continue;
            }

            if (!second) {
                second = read_short(in);
            }

            uint32_t seq = toint(0, second);
            PartialHeader ph(seq);
            in >> ph;

            if (ph.res) {
                throw std::runtime_error("parse_error: header has nonzero res");
            }

            if (ph.cont) {
                // std::cerr << "Patching last buffer with: " << std::hex << ph.cont << std::endl;
                buf[46] = 0xff&(ph.cont>>8);
                buf[47] = 0xff&ph.cont;
            }
            append_sample(buf, block);
            return ph;
        }
        return Header{};
    }

    // fixme: maybe return some summary of headers consumed?
    inline void read_link(std::istream& in, block32_t& block, size_t max_rows = 153) {
        size_t nrows=0;
        while (true) {

            //Header nhead =
            read_package(in, block);

            const size_t drows = block.rows() - nrows;
            nrows = block.rows();

            // std::cerr << "link: nrows: " << nrows << " drows: " << drows << std::endl;

            if (drows < max_rows) {
                return;
            }

        }
    }

    void read_trigger(std::istream& in, block128_t& block) {
        const size_t nrowsin = block.rows();

        size_t nrowshere = 0;
        for (size_t ilink=0; ilink < 4; ++ilink) {
            block32_t link;
            read_link(in, link);
            size_t nrows = link.rows();
            // std::cerr << "trigger: link:" << ilink << " nrows:" << nrows << " nrowsin:" << nrowsin << std::endl;
            if (nrows > nrowshere) {
                nrowshere = nrows;
                block.resize(nrowsin + nrowshere, Eigen::NoChange);
            }
            // block.block(r,c,nr,nc)
            block.block(nrowsin, ilink*32, nrows, 32) = link;
        }        
    }


} // namespace pcbro

#endif
