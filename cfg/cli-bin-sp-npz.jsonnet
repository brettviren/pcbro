local pcbront = import "pcbront.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.npz" \
//   -c cli-bin2npz.jsonent [...]
function(infile, outfile, tag="", nplanes=3,
         resps_file=pcbront.defaults.files.response,
         wires_file=pcbront.defaults.files.wires)
{
    local vol = pcbront.vol(),
    local anode = pcbront.anode(wires_file, vol),
    local resp = pcbront.resp(respf=resps_file),

    local graph = g.pipeline([
        pcbront.io.rawsource("input", infile, tag, nplanes),
        pcbront.io.tentoframe("tensor-to-frame",
                              tensors=[pcbront.io.tensor(tag)]),

        pcbront.sigproc(anode, resp),

        pcbront.io.npzsink("output", outfile, false, tags=["gauss0", "wiener0", "threshold0"]),
        pcbront.io.dumpframes("dumpframes")]),

    seq: pcbront.appcfg(graph)
}.seq

