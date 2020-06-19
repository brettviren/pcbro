#ifndef PCBRO_RAWSOURCE_H_SEEN
#define PCBRO_RAWSOURCE_H_SEEN

#include "WireCellUtil/Units.h"

#include "WireCellIface/IConfigurable.h"
#include "WireCellIface/ITensorSetSource.h"

#include <fstream>
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
        std::ifstream m_fstr;
        bool m_eos{false};
        int m_ident{0};
        double m_tick{0.5*WireCell::units::us};
        std::string m_tag{""};
    };

}

#endif // PCBRO_RAWSOURCE_H_SEEN
