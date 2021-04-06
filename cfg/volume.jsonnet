local wc = import "wirecell.jsonnet";

function(name="pcbro", anode=0, response=10*wc.cm, cathode=38*wc.cm) {
    wires: 0,
    name: name,
    faces: [
        {anode: anode, response: response, cathode: cathode},
        null
    ],
}
