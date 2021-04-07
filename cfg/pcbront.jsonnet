// WCT configuration support for PCB readout components
{

    defaults : import "defaults.jsonnet",

    // Object of functions to help build graph-boundary nodes 
    io :: import "ioutils.jsonnet",

    // Return a volume object passed to other functions.
    vol :: import "volume.jsonnet",

    // Funtion which returns compound object with attributes related
    // to response.  The .pirs attribute is likely what you want.
    resp :: import "response.jsonnet",

    // Function to make an anode configurable.
    anode:: import "anode.jsonnet",

    // Function to make one sigproc configurable.
    sigproc:: import "sigproc.jsonnet",
    
    // Function returning compound object with sim related
    // configurables.  The .pipeline attribute is likely what you
    // want.
    sim :: import "sim.jsonnet",

    // function taking graph returning app cfg sequence
    appcfg :: import "mainseq.jsonnet",
}
