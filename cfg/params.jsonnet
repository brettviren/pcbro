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
        fields: [
            // for now, use totally bogus fields!
            "ub-10-half.json.bz2"
        ],
    },
}

