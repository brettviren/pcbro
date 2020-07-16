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
    rawsource(name, filename, tag="", nplanes=3) :: g.pnode({
        type: 'PcbroRawSource',
        name: name,
        data: {
            filename: filename,
            tag: tag,
            dupind: nplanes == 3,
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

    // Tag rules and fanpipe
    local fanout_tag_rules = [{
      frame: { '.*': 'orig0' },
      trace: { },
    }],

    local fanin_tag_rules = [{
      frame: { '.*': 'framefanin' },
      trace: {
        ['gauss0']: 'gauss0',
        ['wiener0']: 'wiener0',
        ['threshold0']: 'threshold0',
      },
    }],

    fanpipe:: function( pipelines, name='fanpipe', outtags=[] ) {

      local fanmult = std.length(pipelines),
      local fannums = std.range(0, fanmult -1),

      local fanout = g.node({
        type: 'FrameFanout',
        name: name,
        data: {
          multiplicity: fanmult,
          tag_rules: $.fout_tag_rules,
        },
      }, nin=1, nout=fanmult),

      local fanin = g.pnode({
        type: 'FrameFanin',
        name: name,
        data: {
          multiplicity: fanmult,
          tag_rules: $.fin_tag_rules,
          tags: outtags,
        },
      }, nin=fanmult, nout=1),

      ret: g.intern(
        innodes=[fanout],
        outnodes=[fanin],
        centernodes=pipelines,
        edges =
        [g.edge(fanout, pipelines[n], n, 0) for n in std.range(0, fanmult-1)] +
        [g.edge(pipelines[n], fanin, 0, n) for n in std.range(0, fanmult-1)],
        name=name
      ),

    }.ret,

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


    pipelinesp(infile, outfile, tag="", nplanes=3) :: g.pipeline([
        $.rawsource("input", infile, tag, nplanes),
        $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
        $.magnify("output", outfile, false, [ tag ], tools.anodes[0]),
        sp.make_sigproc(tools.anodes[0]),
        $.magnify("output", outfile, true, [ 'gauss0', 'wiener0', 'threshold0'], tools.anodes[0])
    ]),


    bin_sp_mag(infile, outfile, tag="", nplanes=3) :: g.pipeline([
        $.rawsource("input", infile, tag, nplanes),
        $.fanpipe( pipelines=$.pipelinesp(infile, outfile, tag="", nplanes=3), name='fanpipe', outtags=[] ),
        $.dumpframes("dumpframes")
    ]),


    bin_sp_npz(infile, outfile, tag="", nplanes=3) ::
    g.pipeline([
        $.rawsource("input", infile, tag, nplanes),
        $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
        sp.make_sigproc(tools.anodes[0]),
        $.npzsink("output", outfile, false, tags=["gauss0", "wiener0", "threshold0"]),
        $.dumpframes("dumpframes")]),
}
