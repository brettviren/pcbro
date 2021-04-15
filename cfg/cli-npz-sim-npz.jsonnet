// load depos from npz, simulate, write results to npz

local pcbront = import "pcbront.jsonnet";
local wc = import "wirecell.jsonnet";
local g = import "pgraph.jsonnet";

function(depofile, framefile, 
         resps_file=pcbront.defaults.files.responses,
         wires_file=pcbront.defaults.files.wires,
         do_sigproc="no")
{
    local depos = g.pnode({
        type: 'NumpyDepoLoader',
        data: {
            filename: depofile
        }
    }, nin=0, nout=1),

    local vol = pcbront.vol(),
    local anode = pcbront.anode(wires_file, vol),
    local resp = pcbront.resp(respf=resps_file),
    local sim = pcbront.sim(anode, resp.pirs, vol, resp.daq),
    local sigproc = pcbront.sigproc(anode, resp),

    local beg = [depos, sim.pipeline],

    local mid = if do_sigproc == "yes" then [sigproc] else [],

    local tags = if do_sigproc == "yes" then ["gauss0"] else ["orig0"],
    local end = [
        pcbront.io.npzsink("output", framefile, false, tags=tags),
        pcbront.io.dumpframes("dumpframes")],

    local graph = g.pipeline(beg+mid+end),

    seq: pcbront.appcfg(graph)
}.seq
    
