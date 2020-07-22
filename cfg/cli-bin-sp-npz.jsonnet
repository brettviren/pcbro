local pcbro = import "pcbro.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.npz" \
//   -c cli-bin2npz.jsonent [...]
function(infile, outfile, tag="", nplanes=3, resp='pcbro-response-default.json.bz2') {

    local det = pcbro.detector(resp),

    local graph = g.pipeline([
        pcbro.rawsource("input", infile, tag, nplanes),
        pcbro.tentoframe("tensor-to-frame", tensors=[pcbro.tensor(tag)]),
        pcbro.sigproc(det),
        pcbro.npzsink("output", outfile, false, tags=["gauss0", "wiener0", "threshold0"]),
        pcbro.dumpframes("dumpframes")]),

    local app = {
        type: 'Pgrapher',
        data: {
            edges: g.edges(graph)
        },
    },
    local cmdline = {
        type: "wire-cell",
        data: {
            plugins: pcbro.plugins + ["WireCellApps", "WireCellPgraph"],
            apps: ["Pgrapher"],
        }
    },
    seq: [cmdline] + g.uses(graph) + [app],
}.seq

