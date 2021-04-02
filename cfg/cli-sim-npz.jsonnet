// Use a simple line source for depos, run WCT sim, save as Numpy file

local pcbro = import "pcbro.jsonnet";
local wc = import "wirecell.jsonnet";
local g = import "pgraph.jsonnet";

function(outfile, tag="", nplanes=3, resp=pcbro.response_file, do_sigproc=false) {

    local det = pcbro.detector(resp),

    local tracklist = [
        {
            time: 0*wc.ms,
            charge: -5000,
            ray: {
                tail: wc.point(t*5+10, -(2*t), -(2*t +2), wc.cm),
                head: wc.point(t*5   , +(2*t), +(2*t +2), wc.cm),
            }
        } for t in [0,1,2,3,4,5,6,7]],

    local depos = g.pnode({
        type: 'TrackDepos',
        data: {
            step_size: 1.0*wc.mm,
            tracks: tracklist
        },
    }, nin=0, nout=1),

    local tags = if do_sigproc then ["gauss0"] else ["orig0"],

    local beg = [depos, pcbro.sim(det)],
    local mid = if do_sigproc then [pcbro.sigproc(det)] else [],
    local end = [
        pcbro.npzsink("output", outfile, false, tags=tags),
        pcbro.dumpframes("dumpframes")],

    local graph = g.pipeline(beg+mid+end),

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

