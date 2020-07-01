// Use ZIO to sling .bin files to .hdf5
//
// $ rm -f flow.hdf; zio flow-file-server -n zioflow -p flow -v warning cfg/zioflow-rules.jsonnet
//
// $ wire-cell --tla-code infiles="[ $(printf '"%s",' /home/bv/work/pcbro/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_1590486[0-4]*.bin ) ]" -c cfg/cli-pcbro-zio.jsonnet 
//
// Let run and must Ctrl-C the file server twice to get it to close the file and shutdown.
//
// Note, something around 16 files (ie, 16 Zyre ZIO peers) causes Zyre to assert
//
// wire-cell: src/zsock.c:88: zsock_new_checked: Assertion `self->handle' failed.

local g = import "pgraph.jsonnet";

// this is from the WCT UP brettviren/pcbro
local pcbro = import "pcbro.jsonnet";

local make_sender(n=0) =
    g.pnode({
        type: "ZioTensorSetSink",
        name: "ziosink%d"%n,
        data: {
            verbose: 0,             // turns on Zyre verbosity
            timeout: 5000,
            // these are added to the flow object
            attributes: {           
                stream: "flow%d"%n,
            },
            connects: [
                { nodename: "zioflow", portname: "flow" }
            ]
        }
    }, nin=1, nout=0);


local make_pipe(infile, n, tag) =
    g.pipeline([
        pcbro.rawsource("input", infile, tag),
        make_sender(n),
    ]);


function(infiles, grex='TbbFlow') {
    
    local pi = if grex == 'TbbFlow' then ["WireCellTbb"] else [],

    local sgs = [make_pipe(infiles[n],n,"file%04d"%n) for n in std.range(0,std.length(infiles)-1)],
    local graph = g.intern(outnodes=sgs),

    local app = {
        type: grex,
        data: {
            edges: g.edges(graph),
        },
    },

    local cmdline = {
        type: "wire-cell",
        data: {
            plugins: pcbro.plugins + pi + ["WireCellZio", "WireCellApps", "WireCellPgraph"],
            //apps: ["Pgrapher"],
            apps: [grex],
        }
    },

    seq: [cmdline] + g.uses(graph) + [app],
}.seq

