local pcbro = import "pcbro.jsonnet";
local g = import "pgraph.jsonnet";

function(infile, outfile, tag="", nplanes=3, resp=pcbro.response_file) {

    local det = pcbro.detector(resp),

    local depos = g.pnode({
        type: 'BeeDepoSource',
        data: {
            filelist: [infile]
        },
    }, nin=0, nout=1),

    local graph = g.pipeline([
        depos,
        pcbro.sim(det),
        // pcbro.sigproc(det),
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
            plugins: pcbro.plugins + ["WireCellApps", "WireCellPgraph", "WireCellGen"],
            apps: ["Pgrapher"],
        }
    },
    seq: [cmdline] + g.uses(graph) + [app],
}.seq

