local pcbront = import "pcbront.jsonnet";
local cnsn = import "cli-npz-sim-npz.jsonnet";

function(depofile, framefile, 
         resps_file=pcbront.defaults.files.responses,
         wires_file=pcbront.defaults.files.wires)
cnsn(depofile, framefile, resps_file, wires_file, "yes")
