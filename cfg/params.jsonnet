local base = import "pgrapher/common/params.jsonnet";
local wc = import "wirecell.jsonnet";
base {

    det: {
        volumes: [
            {
                wires: 0,
                name: "pcbro",
                faces: [
                    {anode: 0, response: 10*wc.cm, cathode: 38*wc.cm},
                    null],
            }
        ]
    },

    daq: super.daq {
        nticks: 646,
    },

    files: super.files {
        wires: "pcbro-wires.json.bz2",
        // must provide "fields" array 
    },

    sim: super.sim {
        // fixed time mode
        fixed: true,
    },

    // This 'sys' thing is something Hanyu added. 
    // See old wire-cell-cfg commit 5f2cda44.
    // I guess it was to add RCRC
    sys_status: false,
    sys_resp: {
        // I don't know what this does.
        start: 0.0, // -10 * wc.us,
        magnitude: 1.0,
        time_smear: 1.0 * wc.us,
    },

}

