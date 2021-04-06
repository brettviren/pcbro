local wc = import "wirecell.jsonnet";
local g = import 'pgraph.jsonnet';

local default_vol = import "volume.jsonnet";

// Return the one and only anode
function(wires="pcbro-wires.json.bz2",vol = default_vol())
{
    local wireobj = {
        type: "WireSchemaFile",
        data: { filename: wires }
    },

    type : "AnodePlane",
    name : "AnodePlane%d" % vol.wires, 
    data : {
        ident : vol.wires,
        nimpacts: 10, 
        wire_schema: wc.tn(wireobj),
        faces : vol.faces,
    },
    uses: [wireobj],
}
