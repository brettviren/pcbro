local g = import 'pgraph.jsonnet';
local plugins = [
    "WireCellPcbro", "WireCellSio", "WireCellAux",
    "WireCellGen", "WireCellSigProc",
    "WireCellApps", "WireCellPgraph"];

function(graph) {
    local app = {
        type: 'Pgrapher',
        data: {
            edges: g.edges(graph)
        },
    },
    local cmdline = {
        type: "wire-cell",
        data: {
            plugins: plugins,
            apps: ["Pgrapher"],
        }
    },
    seq: [cmdline] + g.uses(graph) + [app],
}.seq
