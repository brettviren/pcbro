local pcbro = import "pcbro.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.root" \
//   -c cli-bin-magraw.jsonent [...]



function(infile, outfile, nplanes=3, start=32, triggers=1, resp='pcbro-response-default.json.bz2') {

    // The tag of "raw" (pre-NF) frames.  It's used in several places
    // and effectively a hard-wired value.
    local orig = "orig0",

    local det = pcbro.detector(resp),

    local rawpipeline(outfile) = g.pipeline([
        pcbro.magnify("rawoutput", outfile, false, [orig], det.anode),
        pcbro.dumpframes("dumpframes")
    ]),
    
    local sppipeline(outfile) = g.pipeline([
        pcbro.sigproc(det),
        pcbro.magnify("spoutput", outfile, true, ["gauss0", "wiener0", "threshold0"], det.anode),
        pcbro.dumpframes("dumpframes")
    ]),
    
    // Tag rules and fanpipe
    local fanout_tag_rules =
        [{ frame: { "": orig },
           trace: { }},
         { frame: { "": [ 'gauss0', 'wiener0', 'threshold0'] },
           trace: { } }
        ],
    
    local backend(outfile, tag="", nplanes=3) = g.fan.sink(
        'FrameFanout',
        [rawpipeline(outfile), sppipeline(outfile)],
        name='fansink',
        tag_rules=fanout_tag_rules ),


    local graph = g.pipeline([
        pcbro.rawsource("input", infile, orig, nplanes, start, triggers),
        pcbro.tentoframe("tensor-to-frame", tensors=[pcbro.tensor(orig)]),
        backend(outfile, orig, nplanes)
    ]),


    // local graph =  pcbro.bin_sp_mag(infile, outfile, "orig0", nplanes, start, triggers),
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
