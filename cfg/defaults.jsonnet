local wc = import "wirecell.jsonnet";

{
    files : {
        wires: "pcbro-wires.json.bz2",
        responses: "pcbro-response-avg.json.bz2",
    },

    elec: {
        gain : 14.0*wc.mV/wc.fC,
        shaping : 2.0*wc.us,
        postgain: 1.0,
    },

    daq: {
        tick: 0.5*wc.us,
        nticks: 1000,
    },
    lar: {
        // Longitudinal diffusion constant
        DL :  7.2 * wc.cm2/wc.s,
        // Transverse diffusion constant
        DT : 12.0 * wc.cm2/wc.s,
        // Electron lifetime
        lifetime : 8*wc.ms,
        // Electron drift speed, assumes a certain applied E-field
        drift_speed : 1.6*wc.mm/wc.us, // at 500 V/cm
        // LAr density
        density: 1.389*wc.g/wc.centimeter3,
        // Decay rate per mass for natural Ar39.
        ar39activity: 1*wc.Bq/wc.kg,
    },
    adc: {
        // A relative gain applied just prior to digitization.  This
        // is not FE gain, see elec for that.
        gain: 1.0,
        
        // Voltage baselines added to any input voltage signal listed
        // in a per plan (U,V,W) array.
        baselines: [900*wc.millivolt,900*wc.millivolt,200*wc.millivolt],
        
        // The resolution (bits) of the ADC
        resolution: 12,
        
        // The voltage range as [min,max] of the ADC, eg min voltage
        // counts 0 ADC, max counts 2^resolution-1.
        fullscale: [0*wc.volt, 2.0*wc.volt],
    },
}

