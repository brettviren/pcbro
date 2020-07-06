#include "WireCellPcbro/RawSource.h"
#include "WireCellPcbro/BinFile.h"

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
    : m_filenum{0}
{
}

pcbro::RawSource::~RawSource()
{
}


WireCell::Configuration pcbro::RawSource::default_configuration() const
{
    WireCell::Configuration cfg;       
    cfg["filename"] = "";       // can also accept an array of files
    cfg["tag"] = "";
    return cfg;
}


void pcbro::RawSource::configure(const WireCell::Configuration& cfg)
{
    auto log = WireCell::Log::logger("pcbro");

    m_tag = get<std::string>(cfg, "tag", "");
    log->debug("RawSource: using tag: \"{}\"", m_tag);

    auto jfn = cfg["filename"];
    if (jfn.empty()) {
        std::runtime_error("pcbro::RawSource: empty input filename");
    }

    m_filenames.clear();
    if (jfn.isString()) {
        m_filenames.push_back(jfn.asString());
    }
    else {
        for (auto jone : jfn) {
            m_filenames.push_back(jone.asString());
        }
    }

    for (auto fname : m_filenames) {
        if(fname.substr(fname.find_last_of(".") + 1) != "bin") {
            std::runtime_error("pcbro::RawSource: currently only supports .bin files, not: " + fname);
        }
        std::fstream fstr(fname, std::ios_base::in | std::ios_base::binary);
        if (!fstr.is_open()) {
            std::runtime_error("pcbro::RawSource: failed to open file: " + fname);
        }
        log->debug("RawSource: using file: {}", fname);
    }
    m_filenum=0;
    bool ok = init_file();
    if (! ok) {
        std::runtime_error("pcbro::RawSource: failed to initialze first file");
    }
}

bool pcbro::RawSource::init_file()
{
    auto log = WireCell::Log::logger("pcbro");

    if (m_filenum >= m_filenames.size()) {
        log->debug("RawSource: end of {} files", m_filenames.size());
        return false;
    }

    std::string fname = m_filenames[m_filenum];
    std::fstream fstr(fname, std::ios_base::in | std::ios_base::binary);
    if (!fstr.is_open()) {
        std::runtime_error("pcbro::RawSource: failed to open file: " + fname);
    }

    m_fpd = pcbro::parse_file_path(fname);

    // slurp!
    m_rd = pcbro::read_raw_data(fstr);
    m_cur = m_rd.begin();
    log->debug("RawSource: open file {}", m_filenames[m_filenum]);
    ++m_filenum;
    return true;
}


bool pcbro::RawSource::operator()(ITensorSet::pointer& ts)
{
    ts = nullptr;
    if (m_eos) {
        return false;
    }

    auto log = WireCell::Log::logger("pcbro");

    // This fills ticks (rows) vs electronics channels (columns).
    pcbro::block128_t block;
    try {
        m_cur = pcbro::make_trigger(block, m_cur, m_rd.end());
    }
    catch (const std::range_error& e) {
        log->debug("RawSource: after {} triggers end of file {}", m_ident, m_filenames[m_filenum-1]);

        bool ok = init_file();
        if (ok) {               // keep going
            return this->operator()(ts);
        }

        m_eos = true;           // next time we return false
        return true;
    }
    catch (const std::runtime_error& d) {
        log->debug("RawSource: after {} triggers bad data in file {}", m_ident, m_filenames[m_filenum-1]);

        bool ok = init_file();
        if (ok) {               // keep going
            return this->operator()(ts);
        }

        m_eos = true;           // next time we return false
        return true;
    }

    ++m_ident;
    log->trace("RawSource: [{}]: #{}: {} ticks", m_tag, m_ident, block.rows());

    // produce tensor set.
    Configuration set_md;
    set_md["ident"] = m_ident;
    set_md["time"] = m_ident*units::ms; // fixme: any meaningful value here?
    set_md["tick"] = m_tick;
    set_md["tags"][0] = m_tag;
    set_md["runTime"] = Json::Value::Int64(m_fpd.seconds);
    set_md["runTime_ms"] = m_fpd.msecs;

    ITensor::vector* itv = new ITensor::vector;

    // Output tensor assumes TRANSPOSE of block: ticks are columns!
    // We also will apply the "physical channel map" so channels
    // (rows) more closely map to wire order.

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


    const size_t nticks = block.rows(); // output is the TRANSPOSE
    const size_t nchans = block.cols(); // of the input block!
    // WCT frame tensor wants float type, rows:chans, cols:ticks so
    // transpose and cast.
    const std::vector<size_t> shape = {nchans, nticks};
    Aux::SimpleTensor<float>* frame = new Aux::SimpleTensor<float>(shape);
    Eigen::Map<Eigen::ArrayXXf> arr((float*) frame->data(), nchans, nticks);
    for (size_t ec = 0; ec < 128; ++ec) {
        size_t out_ind = chanPhy[ec]-1;
        for (int ind=0; ind<block.rows(); ++ind) {
            arr(out_ind, ind) = (float)block(ind, ec);
        }

        // log->trace("RawSource: col({})->row({}) {}", ec, out_ind, arr.row(out_ind).sum()/block.rows());
    }
    log->trace("RawSource: total sum: {}", arr.sum());

    auto& wf_md = frame->metadata();
    wf_md["pad"] = 0;
    wf_md["tbin"] = 0.0;
    wf_md["type"] = "waveform";
    wf_md["tag"] = m_tag;
    itv->push_back(ITensor::pointer(frame));
    
    Aux::SimpleTensor<int>* cht = new Aux::SimpleTensor<int>({128});
    int* chdat = reinterpret_cast<int*>(cht->store().data());
    std::iota(chdat, chdat+128, 1);
    auto& ch_md = cht->metadata();
    ch_md["type"] = "channels";
    ch_md["tag"] = m_tag;
    itv->push_back(ITensor::pointer(cht));

    ts = std::make_shared<Aux::SimpleTensorSet>(m_ident, set_md,
                                                ITensor::shared_vector(itv));

    return true;
}
