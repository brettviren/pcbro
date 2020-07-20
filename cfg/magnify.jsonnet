// Magnifier datadumps for raw ADC and SP data signals

local g = import 'pgraph.jsonnet';
local wc = import 'wirecell.jsonnet';


function( name, filename, usetags, tags, anode ) {

  magnify( name, filename, usetags, tags, anode )
    :: g.pnode({
      type: "MagnifySink",
      name: name ,
      data: {
        output_filename: filename,
        root_file_mode: 'UPDATE',
        frames: tags,
        trace_has_tags: usetags,
        anode: wc.tn(anode),
      }
    }, nin=1, nout=1, uses=[anode] ),

}
