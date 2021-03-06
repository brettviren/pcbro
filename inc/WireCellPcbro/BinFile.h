#ifndef PCBRO_BINFILE_H_SEEN
#define PCBRO_BINFILE_H_SEEN

#include <Eigen/Core>

#include <fstream>
// #include <iostream>             // testing

#include <vector>
/// not until GCC 8.1
// #include <filesystem>

namespace pcbro {

    // A "package" has a header and a sequence of samples.  A package
    // which is shorter than the expected size indicates end of a
    // "link" of data.
    const size_t default_package_size = 0x1df4/2-10;

    // Raw data is read from file as 2byte big-endian shorts.
    using raw_data_t = std::vector<uint16_t>;
    using raw_data_itr = std::vector<uint16_t>::iterator;

    // Link data is raw data inflated to 4byte signed int with header
    // removed and some detailed machinations patched up.
    using link_data_t = std::vector<int>;
    using link_data_itr = link_data_t::iterator;
    using link_data_bitr = std::back_insert_iterator< std::vector<int> >;

    // Cooked data is a 2D Eigen3 array holding 16 bit signed ints
    // with 12 bit values.  A row holds one sample time across 128
    // columns of channels.  Channels are numbered by a convention
    // that orders them by first collection strips and then induction
    // strips.  Electronic channel numbers are not exposed.
    using adc_t = int16_t;
    using block128_t = Eigen::Array<adc_t, Eigen::Dynamic, 128>;


    // Parse a filename for a .bin file path
    // Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_159048405892.bin
    struct FilePathData {
        std::string path;
        std::string wibnn, stepnn, fembnn;
        time_t seconds;
        int msecs;
    };
        
    FilePathData parse_file_path(std::string path) {
        // using fs = std::filesystem;
        // fs::path p = path;
        // auto path = p.stem().string();
        auto slash = path.find_last_of("/");
        if (slash != path.npos) {
            path = path.substr(slash+1);
        }
        auto dot = path.find_last_of(".");
        path = path.substr(0, dot);
        
        FilePathData fpd{path};
        // 0         1         2         3
        // 0123456789012345678901234567890123456789
        // WIB00step18_FEMB_B8_159048405892.bin
        fpd.wibnn = path.substr(3,2);
        fpd.stepnn = path.substr(9,2);
        fpd.fembnn = path.substr(17,2);
        fpd.seconds = atol(path.substr(20,10).c_str());
        fpd.msecs = 10*atoi(path.substr(30,2).c_str());
        return fpd;
    }


    /// Slurp in all raw data from a stream.
    raw_data_t read_raw_data(std::istream& stream) {
        raw_data_t rd;
        while (stream) {
            char buf[2] = {0};
            stream.read(buf, 2);
            // raw data stream is big endian.
            rd.emplace_back( 0xffff&(((0xff & buf[0]) <<8) | (0xff & buf[1])) );
        }
        return rd;
    }
        
    uint32_t word(raw_data_itr it) {
        return 0xffffffff & (((*it) << 16 ) + (*(it+1)));
    }

    /// Find end of a package starting at beg but do not read past
    /// end.  Throws runtime_error if data is corrupt.  Returns end if
    /// no next package is found.
    raw_data_itr seek_package(raw_data_itr beg, raw_data_itr end) {
        auto pkg_cnt0 = word(beg);
        auto pkg_res0 = word(beg+2);
        if (pkg_res0 != 0) {
            throw std::runtime_error("corruption on seek package");
        }
        beg += 4;
        while (beg < end) {
            auto pkg_cnt1 = word(beg);
            auto pkg_res1 = word(beg+2);
            if (pkg_cnt1 == pkg_cnt0 + 1 and pkg_res1 == 0) {
                return beg;
            }
            beg += 1;       // row by row, gonna make this garden grow
        }
        return end;
    }

    /// Append package data to link data.
    void append_link(raw_data_itr beg, raw_data_itr end, link_data_bitr itr) {
        raw_data_itr start = beg + 8;
        if (*start == 0 and (*(start+1) == 0xface or *(start+1) == 0xfeed)) {
            start = beg + 9;
        }
        while (start < end) {
            *itr++ = *start++;
        }
    }

    /// Append to bitr all data in the link starting at beg.  Return
    /// iterator to start of next package or end.
    raw_data_itr make_link(raw_data_itr beg, raw_data_itr end,
                           link_data_bitr bitr,
                           size_t package_size = default_package_size) {
        while (true) {
            auto next = seek_package(beg, end);
            if (next == end) {
                return end;
            }
            append_link(beg, next, bitr);
            size_t psize = std::distance(beg, next);
            if (psize < package_size) {
                //std::cerr << "make_link: " << psize << " " << package_size << std::endl;
                return next;
            }
            beg = next;
        }
        std::runtime_error("impossible");
    }

    /// Unpack one sample across four channels from link data.
    template <typename Derived>
    void unpack_sample4(Eigen::ArrayBase<Derived>&& row, link_data_itr beg) {
        row[ 3] = 0x0fff & ( ( *(beg+0) & 0X0FFF)<<0);
        row[ 2] = 0x0fff & ( ((*(beg+1) & 0X00FF)<<4) + ((*(beg+0) & 0XF000) >> 12));
        row[ 1] = 0x0fff & ( ((*(beg+2) & 0X000F)<<8) + ((*(beg+1) & 0XFF00) >> 8 ));
        row[ 0] = 0x0fff & ( ((*(beg+2) & 0XFFF0)>>4));
    }

    // Unpack one sample across 32 channels from link data.
    template <typename Derived>
    void unpack_sample32(Eigen::ArrayBase<Derived>&& row, link_data_itr beg)
    {
        // adc_t pre = 0;
        // if (*beg == 0xfeed) {
        //     pre = 0x10000;      // why?
        // }

        ++beg;

        unpack_sample4(row.segment(4,4), beg+0);
        // row[ 7].append(pre + ((*(beg+1) & 0X0FFF)<<0));
        // row[ 6].append(pre + ((*(beg+2) & 0X00FF)<<4) + ((*(beg+1) & 0XF000) >> 12));
        // row[ 5].append(pre + ((*(beg+3) & 0X000F)<<8) + ((*(beg+2) & 0XFF00) >> 8 ));
        // row[ 4].append(pre + ((*(beg+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(0,4), beg+3);
        // row[ 3].append(pre + ( *(beg+3+1) & 0X0FFF)<<0);
        // row[ 2].append(pre + ((*(beg+3+2) & 0X00FF)<<4) + ((*(beg+3+1) & 0XF000) >> 12));
        // row[ 1].append(pre + ((*(beg+3+3) & 0X000F)<<8) + ((*(beg+3+2) & 0XFF00) >> 8 ));
        // row[ 0].append(pre + ((*(beg+3+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(12,4), beg+6);
        // row[15].append(pre +  ((*(beg+6+1) & 0X0FFF)<<0));
        // row[14].append(pre +  ((*(beg+6+2) & 0X00FF)<<4) + ((*(beg+6+1) & 0XF000) >> 12));
        // row[13].append(pre +  ((*(beg+6+3) & 0X000F)<<8) + ((*(beg+6+2) & 0XFF00) >> 8 ));
        // row[12].append(pre +  ((*(beg+6+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(8,4), beg+9);
        // row[11].append(pre +  ((*(beg+9+1) & 0X0FFF)<<0));
        // row[10].append(pre +  ((*(beg+9+2) & 0X00FF)<<4) + ((*(beg+9+1) & 0XF000) >> 12));
        // row[ 9].append(pre +  ((*(beg+9+3) & 0X000F)<<8) + ((*(beg+9+2) & 0XFF00) >> 8 ));
        // row[ 8].append(pre +  ((*(beg+9+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(20,4), beg+12);
        // row[23].append(pre +  ((*(beg+12+1) & 0X0FFF)<<0));
        // row[22].append(pre +  ((*(beg+12+2) & 0X00FF)<<4) + ((*(beg+12+1) & 0XF000) >> 12));
        // row[21].append(pre +  ((*(beg+12+3) & 0X000F)<<8) + ((*(beg+12+2) & 0XFF00) >> 8 ));
        // row[20].append(pre +  ((*(beg+12+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(16,4), beg+15);
        // row[19].append(pre +  ( *(beg+12+3+1) & 0X0FFF)<<0);
        // row[18].append(pre +  ((*(beg+12+3+2) & 0X00FF)<<4) + ((*(beg+12+3+1) & 0XF000) >> 12));
        // row[17].append(pre +  ((*(beg+12+3+3) & 0X000F)<<8) + ((*(beg+12+3+2) & 0XFF00) >> 8 ));
        // row[16].append(pre +  ((*(beg+12+3+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(28,4), beg+18);
        // row[31].append(pre +  ((*(beg+12+6+1) & 0X0FFF)<<0));
        // row[30].append(pre +  ((*(beg+12+6+2) & 0X00FF)<<4) + ((*(beg+12+6+1) & 0XF000) >> 12));
        // row[29].append(pre +  ((*(beg+12+6+3) & 0X000F)<<8) + ((*(beg+12+6+2) & 0XFF00) >> 8 ));
        // row[28].append(pre +  ((*(beg+12+6+3) & 0XFFF0)>>4));

        unpack_sample4(row.segment(24,4), beg+21);
        // row[27].append(pre +  ((*(beg+12+9+1) & 0X0FFF)<<0));
        // row[26].append(pre +  ((*(beg+12+9+2) & 0X00FF)<<4) + ((*(beg+12+9+1) & 0XF000) >> 12));
        // row[25].append(pre +  ((*(beg+12+9+3) & 0X000F)<<8) + ((*(beg+12+9+2) & 0XFF00) >> 8 ));
        // row[24].append(pre +  ((*(beg+12+9+3) & 0XFFF0)>>4));
    }

    /// Unpack link data to array.  Array is assumed to be sized large
    /// enough.
    template <typename Derived>
    void unpack_link(Eigen::ArrayBase<Derived>&& block, link_data_itr beg, link_data_itr end) {
        Eigen::Index irow = 0;

        while (irow < block.rows() and beg < end+25) {
            unpack_sample32(block.row(irow), beg);
            ++irow;
            beg += 25;
        }
    }


    /// Unpack one trigger of four links.  Return the start of the
    /// next package or end.  Throws range_error if attempt to read
    /// past raw data.
    raw_data_itr make_trigger(block128_t& block,
                              raw_data_itr beg, raw_data_itr end,
                              size_t package_size = default_package_size) {
        for (int ilink=0; ilink < 4; ++ilink) {
            link_data_t ld;
            auto next = make_link(beg, end, link_data_bitr(ld), package_size);
            if (next == end and ilink < 3) {
                throw std::range_error("short read");
            }
            beg = next;

            size_t nticks = ld.size() / 25;
            if (nticks > (size_t)block.rows()) {
                block.resize(nticks, Eigen::NoChange);
            }
            unpack_link(block.block(0, ilink*32, nticks, 32), ld.begin(), ld.end());
        }
        return beg;
    }
}

#endif
