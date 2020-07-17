// WCT configuration support for PCB readout components
local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';

local params = import "params.jsonnet";
local tools_maker = import "pgrapher/common/tools.jsonnet";
local tools = tools_maker(params);

local sp_maker = import "sp.jsonnet";
local sp = sp_maker(params, tools);

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


    ////////////////////////////////////////////////////////////////////////////

    // Magnifier datadumps for raw ADC and SP data signals

    magnify( name, filename, usetag, frames, anode ) :: g.pnode({
        type: "MagnifySink",
        name: name ,
        data: {
            output_filename: filename,
            root_file_mode: 'UPDATE',
            frames: frames,
            trace_has_tags: usetag,
            anode: wc.tn(anode),
        }}, nin=1, nout=1, uses=[anode] ),


    ////////////////////////////////////////////////////////////////////////////


    // Return graph to convert from pcbro .bin to .npz
    bin_npz(infile, outfile, tag="", nplanes=3) ::
    g.pipeline([$.rawsource("input", infile, tag, nplanes),
                $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
                $.npzsink("output", outfile, tags=[tag]),
                $.dumpframes("dumpframes")]),

    bin_mag(infile, outfile, tag="", nplanes=3) ::
    g.pipeline([
                $.rawsource("input", infile, tag, nplanes),
                $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
                $.magnify("output", outfile, true, [ tag ], tools.anodes[0]),
                $.dumpframes("dumpframes")
                ]),




    rawpipeline(infile, outfile, tag)
    :: g.pipeline([
      $.magnify("rawoutput", outfile, true, [ tag ], tools.anodes[0]),
      $.dumpframes("dumpframes")
    ]),

    sppipeline(infile, outfile)
    :: g.pipeline([
      sp.make_sigproc(tools.anodes[0]),
      $.magnify("spoutput", outfile, true, [ 'gauss0', 'wiener0', 'threshold0'], tools.anodes[0]),
      $.dumpframes("dumpframes")
    ]),

    // Tag rules and fanpipe
    local fanout_tag_rules = [{
      frame: { '.*': "orig0" },
      trace: { },
    }],

    backend(infile, outfile, tag="", nplanes=3) ::
    g.fan.sink( 'FrameFanout',
                [$.rawpipeline(infile, outfile, tag), $.sppipeline(infile, outfile)],
                name='fansink',
                tag_rules=fanout_tag_rules
              ),

    bin_sp_mag(infile, outfile, tag="", nplanes=3, start=0, triggers=50) :: g.pipeline([
      $.rawsource("input", infile, tag, nplanes, start, triggers),
      $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
      $.backend(infile, outfile, tag, nplanes)
    ]),




    bin_sp_npz(infile, outfile, tag="", nplanes=3) ::
    g.pipeline([
        $.rawsource("input", infile, tag, nplanes),
        $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
        sp.make_sigproc(tools.anodes[0]),
        $.npzsink("output", outfile, false, tags=["gauss0", "wiener0", "threshold0"]),
        $.dumpframes("dumpframes")]),
}
