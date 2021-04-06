// This adds sigproc to cli-sim-npz in order to give a similar "data
// tier" name ("ssp" vs "sim").

local csn = import "cli-sim-npz.jsonnet";

local pcbront = import "pcbront.jsonnet";
local defaults = pcbront.defaults;

function(outfile,
         resps_file=defaults.files.responses,
         wires_file=defaults.files.wires)
csn(outfile, resps_file, wires_file, true)
