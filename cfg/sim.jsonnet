local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';

local defaults = import "defaults.jsonnet";
function(anode, pirs, vol, daq, lar = defaults.lar, adc=defaults.adc) {

    random : {
        type: "Random",
        data: {
            generator: "default",
            seeds: [0,1,2,3,4],
        }
    },

    drifter: g.pnode({
        local xregions = wc.unique_list(vol.faces),

        type: "Drifter",
        data: lar {
            rng: wc.tn($.random),
            xregions: xregions,
            time_offset: 0.0,

            fluctuate: true, 
        },
    }, nin=1, nout=1, uses=[$.random]),

    bagger: g.pnode({
        type:'DepoBagger',
        data: {
            gate: [0, daq.nticks*daq.tick],
        },
    }, nin=1, nout=1),

    ductor:  g.pnode({
        type:'DepoTransform',
        data: {
            rng: wc.tn($.random),
            anode: wc.tn(anode),
            pirs: [wc.tn(p) for p in pirs],
            fluctuate: true,
            drift_speed: lar.drift_speed,
            first_frame_number: 0,
            readout_time: daq.nticks*daq.tick, 
            start_time: 0,
            tick: daq.tick,
            nsigma: 3,
        },
    }, nin=1, nout=1, uses=pirs + [anode, $.random]),

    reframer : g.pnode({
        type: 'Reframer',
        data: {
            anode: wc.tn(anode),
            tags: [],
            fill: 0.0,
            tbin: 0,
            toffset: 0,
            nticks: daq.nticks,
        },
    }, nin=1, nout=1),
    digitizer : g.pnode({
        type: "Digitizer",
        data : adc {
            anode: wc.tn(anode),
            frame_tag: "orig0"
        }
    }, nin=1, nout=1, uses=[anode]),
    
    pipeline: g.pipeline([$.drifter, $.bagger, $.ductor, $.reframer, $.digitizer])
}
