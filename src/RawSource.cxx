#include "WireCellPcbro/RawSource.h"
#include "WireCellPcbro/BinStream.h"

#include "WireCellAux/SimpleTensor.h"
#include "WireCellAux/SimpleTensorSet.h"

#include "WireCellIface/IConfigurable.h"

#include "WireCellUtil/NamedFactory.h"
#include "WireCellUtil/Logging.h"


#include <numeric>

WIRECELL_FACTORY(PcbroRawSource, pcbro::RawSource,
                 WireCell::IConfigurable, WireCell::ITensorSetSource)

using namespace WireCell;

pcbro::RawSource::RawSource()
{
}

pcbro::RawSource::~RawSource()
{
}


WireCell::Configuration pcbro::RawSource::default_configuration() const
{
    WireCell::Configuration cfg;       
    cfg["filename"] = "";
    cfg["tag"] = "";
    return cfg;
}


void pcbro::RawSource::configure(const WireCell::Configuration& cfg)
{
    std::string fname = get<std::string>(cfg, "filename", "");
    if (fname.empty()) {
        std::runtime_error("pcbro::RawSource: empty input filename");
    }

    if(fname.substr(fname.find_last_of(".") + 1) != "bin") {
        std::runtime_error("pcbro::RawSource: currently only supports .bin files");
    }

    m_fstr.open(fname, std::ios_base::in | std::ios_base::binary);
    if (!m_fstr.is_open()) {
        std::runtime_error("pcbro::RawSource: failed to open file: " + fname);
    }

    m_tag = get<std::string>(cfg, "tag", "");

    // Prime pump.  fixme: this should be hidden in BinStream somehow
    pcbro::Header header;
    m_fstr >> header;
    if (header.res) {
        std::runtime_error("pcbro::RawSource: file corrupt: " + fname);
    }
}

bool pcbro::RawSource::operator()(ITensorSet::pointer& ts)
{
    ts = nullptr;
    if (m_eos) {
        return false;
    }

    pcbro::block128_t block;
    try {
        pcbro::read_trigger(m_fstr, block);
    }
    catch (const std::range_error& e) {
        auto log = WireCell::Log::logger("pcbro");
        log->debug("pcbro: end of file");
        m_eos = true;           // next time we return false
        return true;
    }

    ++m_ident;

    // produce tensor set.
    Configuration set_md;
    set_md["time"] = m_ident*units::s; // fixme: any meaningful value here?
    set_md["tick"] = m_tick;

    ITensor::vector* itv = new ITensor::vector;

    const size_t nticks = block.rows();
    const size_t nchans = block.cols();
    const std::vector<size_t> shape = {nchans, nticks};
    Aux::SimpleTensor<float>* frame = new Aux::SimpleTensor<float>(shape);
    Eigen::Map<Eigen::ArrayXXf> arr((float*) frame->data(), nticks, nchans);
    arr = block.cast<float>();

    auto& wf_md = frame->metadata();
    wf_md["tag"] = m_tag;
    wf_md["pad"] = 0;
    wf_md["tbin"] = 0.0;
    wf_md["type"] = "waveform";
    itv->push_back(ITensor::pointer(frame));
    
    // Copied from "dataConversion.py".  Map electronics channel index
    // to a "physical" channel.  Collection runs over [0,61],
    // induction over [62,127].  Relative handedness is not yet known.
    const std::vector<int> chanPhy =
        {65, 66, 67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,
         85,86,87,88,89,90,91,92,93,94,95,96,113,114,115,116,117,118,119,
         120,121,122,123,124,125,126,127,128,97,98,99,100,101,102,103,
         104,105,106,107,108,109,110,111,112,16,15,14,13,12,11,10,9,8,
         7,6,5,4,3,2,1,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,
         64,63,62,61,60,59,58,57,56,55,54,53,52,51,50,49,48,47,46,45,44,
         43,42,41,40,39,38,37,36,35,34,33};

    Aux::SimpleTensor<int>* cht = new Aux::SimpleTensor<int>({chanPhy.size()});
    memcpy(cht->store().data(), chanPhy.data(), cht->size());
    auto& ch_md = cht->metadata();
    ch_md["type"] = "channels";
    ch_md["tag"] = m_tag;
    itv->push_back(ITensor::pointer(cht));

    ts = std::make_shared<Aux::SimpleTensorSet>(m_ident, set_md,
                                                ITensor::shared_vector(itv));

    return true;
}
