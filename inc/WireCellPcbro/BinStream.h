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

        
    // This helps unpack the 4x12 bit samples which are packed in to 6
    // bytes.  This bitfield struct provides the unpacking.
    struct SampleFour {
        // We only care about the first 6 bytes
        uint64_t d:12, c:12, b:12, a:12;
        // The above alone typically will pad out to 8 bytes for
        // proper alignment and we add that explicitly.  When mapped
        // to packed data, it will contain only garbage.
        uint16_t pading{0};
    };

    // Append four consequtive samples to row irow to four consequtive waveforms starting at icol.
    // Return the column index one past what was filled.
    inline Eigen::Index fill4(block32_t& block, Eigen::Index irow, Eigen::Index icol, SampleFour& s) {
        block(irow, icol++) = s.a;
        block(irow, icol++) = s.b;
        block(irow, icol++) = s.c;
        block(irow, icol++) = s.d;
        return icol;
    }

    inline void append_sample(char buf[], block32_t& block) {
        Eigen::Index irow = block.rows();
        block.resize(irow+1, Eigen::NoChange);
        //std::cerr << "appending: " << irow << std::endl;

        Eigen::Index icol = 0;
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[6]);
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[0]);
        
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[18]);
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[12]);

        icol = fill4(block, irow, icol, *(SampleFour*)&buf[30]);
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[24]);
        
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[42]);
        icol = fill4(block, irow, icol, *(SampleFour*)&buf[36]);
    }

    // Read one 32-channel sample and append to block.
    inline void read_sample(std::istream& s, block32_t& block) {

        // load in 24 shorts with 32x12 bits
        char buf[48];
        s.read(buf, 48);
        append_sample(buf, block);
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
                // It seems the DAQ can start saving without breaking into packages.
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

            // const uint16_t tailm1 = 0xffff&(((0xff & buf[44]) <<8) | (0xff & buf[45]));
            // const uint16_t tailm0 = 0xffff&(((0xff & buf[46]) <<8) | (0xff & buf[47]));
            //std::cerr << std::hex << first << " " << second << " " << tailm1 << " " << tailm0 << std::endl;
            uint32_t seq = toint(0, second);
            PartialHeader ph(seq);
            in >> ph;

            // std::cerr << "Header: seq:" << std::dec << ph.seq
            //           << " res:" << ph.res
            //           << " cont:" << std::hex << ph.cont << std::endl;

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
