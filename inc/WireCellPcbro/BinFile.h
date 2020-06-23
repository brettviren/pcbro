#ifndef PCBRO_BINFILE_H_SEEN
#define PCBRO_BINFILE_H_SEEN

#include <Eigen/Core>

#include <fstream>
#include <iostream>             // testing
#include <vector>

namespace pcbro {

    const size_t default_package_size = 0x1df4/2-10;

    using raw_data_t = std::vector<uint16_t>;
    using raw_data_itr = std::vector<uint16_t>::const_iterator;

    using link_data_t = std::vector<int>;
    using link_data_bitr = std::back_insert_iterator< std::vector<int> >;

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

    // Append package data to link data
    void append_link(raw_data_itr beg, raw_data_itr end, link_data_bitr itr) {
        raw_data_itr start = beg + 8;
        if (*start == 0 and (*(start+1) == 0xface or *(start+1) == 0xfeed)) {
            start = beg + 9;
        }
        while (start < end) {
            *itr++ = *start++;
        }
    }

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
                std::cerr << "make_link: " << psize << " " << package_size << std::endl;
                return next;
            }
            beg = next;
        }
        std::runtime_error("impossible");
    }

    using adc_t = int16_t;
    using block128_t = Eigen::Array<adc_t, Eigen::Dynamic, 128>;

    using link_data_citr = link_data_t::const_iterator;

    // unpack four channels
    template <typename Derived>
    void unpack_sample4(Eigen::ArrayBase<Derived>&& row, link_data_citr beg) {
        row[ 3] = 0x0fff & ( ( *(beg+0) & 0X0FFF)<<0);
        row[ 2] = 0x0fff & ( ((*(beg+1) & 0X00FF)<<4) + ((*(beg+0) & 0XF000) >> 12));
        row[ 1] = 0x0fff & ( ((*(beg+2) & 0X000F)<<8) + ((*(beg+1) & 0XFF00) >> 8 ));
        row[ 0] = 0x0fff & ( ((*(beg+2) & 0XFFF0)>>4));
    }

    // Unpack one 32 channel sample array
    template <typename Derived>
    void unpack_sample32(Eigen::ArrayBase<Derived>&& row, link_data_citr beg)
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

    template <typename Derived>
    void unpack_link(Eigen::ArrayBase<Derived>&& block, link_data_citr beg, link_data_citr end) {
        Eigen::Index irow = 0;

        while (irow < block.rows() and beg < end+25) {
            unpack_sample32(block.row(irow), beg);
            ++irow;
            beg += 25;
        }
    }


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
