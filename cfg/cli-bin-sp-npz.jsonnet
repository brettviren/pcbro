local pcbro = import "pcbro.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.npz" \
//   -c cli-bin2npz.jsonent [...]
function(infile, outfile, tag="", nplanes=3) {


    local graph = pcbro.bin_sp_npz(infile, outfile, tag, nplanes),

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

