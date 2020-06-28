// WCT configuration support for PCB readout components
local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';
{
    plugins: ["WireCellPcbro", "WireCellSio", "WireCellAux", "WireCellGen"],

    // Return a raw source configuration node to read in a .bin file
    // and produce tensors with given tag.
    rawsource(name, filename, tag="") :: g.pnode({
        type: 'PcbroRawSource',
        name: name,
        data: {
            filename: filename,
            tag: tag
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

    // Return graph to convert from pcbro .bin to .npz
    bintonpz(infile, outfile, tag="") ::
    g.pipeline([$.rawsource("input", infile, tag),
                $.tentoframe("tensor-to-frame", tensors=[$.tensor(tag)]),
                $.npzsink("output", outfile, tags=[tag]),
                $.dumpframes("dumpframes")]),
}

