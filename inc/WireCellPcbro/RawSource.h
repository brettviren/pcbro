#ifndef PCBRO_RAWSOURCE_H_SEEN
#define PCBRO_RAWSOURCE_H_SEEN

#include "WireCellIface/IConfigurable.h"

namespace pcbro {

class RawSource : public WireCell::IConfigurable {
  public:
    virtual ~RawSource();

    // IConfigurable interface
    WireCell::Configuration default_configuration() const;
    void configure(const WireCell::Configuration& cfg);

};

}

#endif // PCBRO_RAWSOURCE_H_SEEN