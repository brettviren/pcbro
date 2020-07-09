#ifndef PCBRO_RAWSOURCE_H_SEEN
#define PCBRO_RAWSOURCE_H_SEEN

#include "WireCellPcbro/BinFile.h"

#include "WireCellUtil/Units.h"

#include "WireCellIface/IConfigurable.h"
#include "WireCellIface/ITensorSetSource.h"

#include <string>

namespace pcbro {

    class RawSource : public WireCell::ITensorSetSource,  WireCell::IConfigurable {
    public:
        RawSource();
        virtual ~RawSource();

        // IConfigurable interface
        WireCell::Configuration default_configuration() const;
        void configure(const WireCell::Configuration& cfg);

        
        // ITensorSetSource interface
        virtual bool operator()(WireCell::ITensorSet::pointer& ts);

    private:

        // info about current .bin file
        pcbro::raw_data_t m_rd;
        pcbro::raw_data_itr m_cur;
        pcbro::FilePathData m_fpd;

        // We can handle one or many files.
        std::vector<std::string> m_filenames;
        size_t m_filenum;

        bool m_eos{false}, m_dupind{false};
        int m_ident{0};
        double m_tick{0.5*WireCell::units::us};
        std::string m_tag{""};

        bool init_file();
    };

}

#endif // PCBRO_RAWSOURCE_H_SEEN
