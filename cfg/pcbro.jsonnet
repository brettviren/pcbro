// WCT configuration support for PCB readout components
local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';

local params = import "params.jsonnet";
local tools_maker = import "pgrapher/common/tools.jsonnet";
local tools = tools_maker(params);


{

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


    // Produce params and tools objects that describe the pcbro detector.
    detector(resp = 'pcbro-response-default.json.bz2'):: {
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
