// WCT configuration support for PCB readout components
local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';

local params = import "params.jsonnet";
local tools_maker = import "pgrapher/common/tools.jsonnet";
local tools = tools_maker(params);


{
    // this may be used to set a default
    response_file: "pcbro-response-avg.json.bz2",

    plugins: ["WireCellPcbro", "WireCellSio", "WireCellAux", "WireCellGen", "WireCellSigProc"],

    // Return a raw source configuration node to read in a .bin file
    // and produce tensors with given tag.
    rawsource(name, filename, tag="", nplanes=3, start=1, triggers=50) :: g.pnode({
        type: 'PcbroRawSource',
        name: name,
        data: {
            filename: filename,
            tag: tag,
            dupind: nplanes == 3,
            start_trigger: start,
            triggers: triggers,
        }}, nin=0, nout=1),

    // Return a tensor (sub)configuration
    tensor(tag) :: {
        tag: tag
    },

    // default is to convert only the empty string tag.
    tentoframe(name, tensors = [{}]) :: g.pnode({
        type: 'TaggedTensorSetFrame',
        name: name,
        data: {
            tensors: tensors,
        }}, nin=1, nout=1),

    // Return a numpy frame saver configuration.
    npzsink(name, filename, digitize=true, tags=[]) :: g.pnode({
        type: 'NumpyFrameSaver',
        name: name,
        data: {
            filename: filename,
            digitize: digitize,
            frame_tags: tags,
        }}, nin=1, nout=1),

    dumpframes(name) :: g.pnode({
        type: "DumpFrames",
        name: name,
    }, nin=1, nout=0),

    //
    // Redo this from pgrapher/common/tools.jsonnet in order to fix "padding"
    //
    local sim_response_binning = {
        tick: params.daq.tick,
        nticks: params.sim.ductor.nticks, // MUST match ductor
    },
    mypirs :: std.mapWithIndex(function (n, fr) [
        {
            type: "PlaneImpactResponse",
            name : "MyPIR%splane%d" % [fr.name, plane],
            data : sim_response_binning {
                plane: plane,
                field_response: wc.tn(fr),
                short_responses: [wc.tn(tools.elec_resp)],
                // this needs to be big enough for convolving FR*CE
                overall_short_padding: 2000*wc.us,
                long_responses: [wc.tn(tools.rc_resp)],
                // this needs to be big enough to convolve RC
                long_padding: 1.5*wc.ms,
            },
            uses: [fr, tools.elec_resp, tools.rc_resp],
        } for plane in [0,1,2]], tools.fields),

    // Produce params and tools objects that describe the pcbro detector.
    detector(resp = self.response_file):: {
        local defp = import "params.jsonnet",
        local tools_maker = import "pgrapher/common/tools.jsonnet",
        params: defp {
            files: super.files {
                wires: "pcbro-wires.json.bz2",
                fields: [ resp ]}},
        tools: tools_maker(self.params),
        anode: tools.anodes[0],
    },

    // Return a sigproc node for detector
    sigproc(detector):: {
        local sp_maker = import "sp.jsonnet",
        local sp = sp_maker(detector.params, detector.tools),
        ret: sp.make_sigproc(detector.anode)
    }.ret,

    sim(detector) :: {
        local sim_maker = import "pgrapher/common/sim/nodes.jsonnet",
        local sim = sim_maker(detector.params, detector.tools),
        local drifter = sim.drifter,
        local bagger = sim.make_bagger(),
        local ductor = sim.make_depotransform("ductor", detector.anode, detector.tools.mypirs[0]),
        local reframer = g.pnode({
            type: 'Reframer',
            name: 'reframer',
            data: {
                anode: wc.tn(detector.anode),
                tags: [],
                fill: 0.0,
                tbin: detector.params.sim.reframer.tbin,
                toffset: 0,
                nticks: detector.params.sim.reframer.nticks,
            },
        }, nin=1, nout=1),
        local digitizer = sim.digitizer(detector.anode, name="digitizer", tag="orig0"),
        ret: g.pipeline([drifter, bagger, ductor, reframer, digitizer])
    }.ret,

    // return a magnify node
    magnify(name, filename, usetags, tags, anode ) :: g.pnode({
        type: "MagnifySink",
        name: name ,
        data: {
            output_filename: filename,
            root_file_mode: 'UPDATE',
            frames: tags,
            trace_has_tags: usetags,
            anode: wc.tn(anode),
        }
    }, nin=1, nout=1, uses=[anode] ),

}
