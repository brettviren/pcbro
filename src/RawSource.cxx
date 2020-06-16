#include "WireCellPcbro/RawSource.h"

#include "WireCellIface/IConfigurable.h"
#include "WireCellUtil/NamedFactory.h"
#include "WireCellUtil/Logging.h"

pcbro::RawSource::~RawSource()
{
}


WireCell::Configuration pcbro::RawSource::default_configuration() const
{
    WireCell::Configuration cfg;       
    cfg["param"] = "value";
    return cfg;
}


void pcbro::RawSource::configure(const WireCell::Configuration& cfg)
{
    auto log = WireCell::Log::logger("pcbro");
    log->info(cfg);
};

// dump example.  normally, more ifaces than just configurable
WIRECELL_FACTORY(PcbroRawSource, pcbro::RawSource,
                 WireCell::IConfigurable)