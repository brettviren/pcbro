local pcbro = import "pcbro.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.root" \
//   -c cli-bin-magraw.jsonent [...]
//
// infile may also be an array
function(infile, outfile, nplanes=3) {

    local tag = "orig0",

    local det = pcbro.detector(),

    // Return graph to convert from pcbro .bin to .root
    local graph = g.pipeline([
        pcbro.rawsource("input", infile, tag, nplanes),
        pcbro.tentoframe("tensor-to-frame", tensors=[pcbro.tensor(tag)]),
        pcbro.magnify("output", outfile, true, [ tag ], det.anode),
        pcbro.dumpframes("dumpframes")
    ]),

    local app = {
        type: 'Pgrapher',
        data: {
            edges: g.edges(graph)
        },
    },
    local cmdline = {
        type: "wire-cell",
        data: {
            plugins: pcbro.plugins + ["WireCellApps", "WireCellPgraph", "WireCellRoot"],
            apps: ["Pgrapher"],
        }
    },
    seq: [cmdline] + g.uses(graph) + [app],
}.seq
