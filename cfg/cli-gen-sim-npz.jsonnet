// Use a simple line source for depos, run WCT sim, save as Numpy file

local pcbront = import "pcbront.jsonnet";
local wc = import "wirecell.jsonnet";
local g = import "pgraph.jsonnet";

function(outfile, 
         resps_file=pcbront.defaults.files.responses,
         wires_file=pcbront.defaults.files.wires,
         first_track="1",
         last_track="7",
         do_sigproc=false)
{

    local vol = pcbront.vol(),
    local anode = pcbront.anode(wires_file, vol),
    local resp = pcbront.resp(respf=resps_file),
    local sim = pcbront.sim(anode, resp.pirs, vol, resp.daq),
    local sigproc = pcbront.sigproc(anode, resp),

    local tracklist = [
        {
            time: 0*wc.ms,
            charge: -5000,
            ray: {
                tail: wc.point(t*5+10, -(2*t), -(2*t + 0.1), wc.cm),
                head: wc.point(t*5   , +(2*t), +(2*t + 0.1), wc.cm),
            }
        } for t in std.range(std.parseInt(first_track),std.parseInt(last_track))],

    local depos = g.pnode({
        type: 'TrackDepos',
        data: {
            step_size: 1.0*wc.mm,
            tracks: tracklist
        },
    }, nin=0, nout=1),

    local beg = [depos, sim.pipeline],

    local mid = if do_sigproc then [sigproc] else [],

    local tags = if do_sigproc then ["gauss0"] else ["orig0"],
    local end = [
        pcbront.io.npzsink("output", outfile, false, tags=tags),
        pcbront.io.dumpframes("dumpframes")],

    local graph = g.pipeline(beg+mid+end),

    seq: pcbront.appcfg(graph)
}.seq

