// Return configurables for things related to response
local wc = import "wirecell.jsonnet";

local defaults = import "defaults.jsonnet";

// daq, elec is from eg params
function(respf = defaults.files.response, daq=defaults.daq, elec=defaults.elec) {

    daq: daq,
    elec: elec,


    field_resp : {
        type: "FieldResponse",
        name: respf,
        data: {
            filename: respf
        }
    },

    local binning = { nticks: daq.nticks, tick: daq.tick },

    rc_resp : {
        type: "RCResponse",
        data: binning {
            width: 1.0*wc.ms,
        }
    },

    elec_resp : {
        type: "ColdElecResponse",
        data: binning {
            shaping: elec.shaping,
            gain: elec.gain,
            postgain: elec.postgain,
        },            
    },

    pirs : [ {
        type: "PlaneImpactResponse",
        name : "PIRplane%d" % plane,
        data : {
            plane: plane,
            field_response: wc.tn($.field_resp),
            short_responses: [wc.tn($.elec_resp)],
            // this needs to be big enough for convolving FR*CE
            overall_short_padding: 200*wc.us,
            long_responses: [wc.tn($.rc_resp)],
            // this needs to be big enough to convolve RC
            long_padding: 1.5*wc.ms,
        },
        uses: [$.field_resp, $.elec_resp, $.rc_resp],
    } for plane in [0,1,2]],
}
