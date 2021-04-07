local pcbront = import "pcbront.jsonnet";
local g = import "pgraph.jsonnet";

// Return a wire-cell CLI sequence.
// This can be used with TLA from the command line like:
// wire-cell \
//   --tla-str infile="file.bin" \
//   --tla-str outfile="file.npz" \
//   -c cli-bin2npz.jsonent [...]
//
// infile may also be an array
function(infile, outfile, nplanes=3) 
pcbront.appcfg(g.pipeline([
    pcbront.io.rawsource("input", infile, nplanes=nplanes),
    pcbront.io.tentoframe("tensor-to-frame"),
    pcbront.io.npzsink("output", outfile),
    pcbront.io.dumpframes("dumpframes")]))
