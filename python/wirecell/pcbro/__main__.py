'''
Main CLI to moo
'''
import os
import os.path as osp
import sys
import json
import click
from wirecell import units

import wirecell.pcbro.garfield as pcbgf
import wirecell.pcbro.draw as pcbdraw
import wirecell.pcbro.holes as pcbholes

def sourceme(source):
    '''
    Convert a tar file or directory path into a source
    '''
    if osp.splitext(source)[1] in ['.tar', '.tgz']:
        return pcbgf.tar_source(source)
    if osp.isdir(source):
        return pcbgf.dir_source(source, ['ind'])
    raise ValueError(f"Unsupported source: {source}")

@click.group()
@click.pass_context
def cli(ctx):
    '''
    wirecell-pcbro command line interface
    '''
    ctx.ensure_object(dict)

@cli.command("convert-garfield")
@click.option("-o", "--origin", default="10.0*cm",
              help="Set drift origin (give units, eg '10*cm').")
@click.option("-s", "--speed", default="1.6*mm/us",
              help="Set nominal drift speed (give untis, eg '1.6*mm/us').")
@click.option("-n", "--normalization", default=0.0,
              help="Set normalization: 0:none, <0:electrons, >0:multiplicative scale.  def=0")
@click.option("-z", "--zero-wire-locs", default=[0.0,0.0,0.0], nargs=3, type=float,
              help="Set location of zero wires.  def: 0 0 0")
@click.option("-f", "--format", default="json.bz2",
              type=click.Choice(['json', 'json.gz', 'json.bz2']),
              help="Set output file format")
@click.option("-b", "--basename", default="pcbro-response",
              help="Set basename for output files")
@click.argument("garfield-fileset")

def convert_garfield(origin, speed, normalization, zero_wire_locs,
                     format,
                     garfield_fileset, basename):
    '''
    Produce variants of WCT field files from tarfile of Garfield output text files.

    See also same subcommand from wirecell-sigproc
    '''
    import wirecell.pcbro.garfield as gar
    from wirecell.sigproc.response import rf1dtoschema
    import wirecell.sigproc.response.persist as per

    origin = eval(origin, units.__dict__)
    speed = eval(speed, units.__dict__)
    if format.startswith('.'):
        format = format[1:]

    slices = {
        'avg': dict(u=[0,1], v=[0,1], w=[0,1]),
        'slc0': dict(u=[0,1], v=[0], w=[0]),
        'slc1': dict(u=[0,1], v=[1], w=[1]),
    }


    ripem = gar.Ripem(sourceme(garfield_fileset))
    sipem = gar.Sipem(ripem)

    fnames = list()
    for name, slcs in slices.items():
        fr = sipem.inschema(speed, origin, slcs['u'], slcs['v'], slcs['w'])
        fname = basename + '-' + name + '.' + format
        per.dump(fname, fr)
        print (fname)
        fnames.append(fname)
    print('\n'.join(fnames))

    # rflist = sipem.asrflist(strategy)
    # print("made %d response functions" % len(rflist))
    # fr = rf1dtoschema(rflist, origin, speed)
    # per.dump(wirecell_field_response_file, fr)


@cli.command("convert-garfield-npz")
@click.option("-o","--output",default=None, help="Output .npz file")
@click.argument("datfile")
def convert_garfield_npz(output, datfile):
    '''
    Convert one Garfield .dat file to a .npz file
    '''
    if not output:
        output = os.path.splitext(os.path.basename(datfile))[0] + ".npz"
    pcbgf.dat2npz(datfile, output)    


@cli.command("plot-garfield-micro-wires")
@click.option("-o","--output", default="garfield-micro-wires.pdf", help="Output PDF file")
@click.argument("source")
def plot_garfield_micro_wires(output, source):
    pcbgf.draw_file(source, output)

@cli.command("plot-garfield")
@click.option("-o","--output", default="garfield-plots.pdf", help="Output PDF file")
@click.argument("source")
def plot_garfield(output, source):
    '''Plot responses after parsing garfield, and applying integrating map.  

    What you see should be reasonably what comes out as .json.bz2 with
    convert-garfield.

    '''
    source = sourceme(source)
    pcbgf.plots(source, output)

@cli.command("plot-holes")
@click.option("-s", "--strips", default=5, help="Number of strips")
@click.option("-p", "--plane", default="col", help="Plane to draw")
@click.option("-o","--output", default="pcbro-holes.pdf", help="Output PDF file")
def plot_holes(strips, plane,output):
    '''
    Make some artwork which "obviously" shows the integration map is correct.
    '''
    if plane=="ind":
        pg = pcbholes.Induction()
    elif plane=="col":
        pg = pcbholes.Collection()
    else:
        raise RuntimeError(f'no such plane {plane}')
    pcbdraw.holes_planegeometry(pg, pdf_file=output, strips=range(-strips, strips+1))

@cli.command("list-holes")
@click.option("-s", "--strips", default=5, help="Number of strips")
@click.option("-S", "--slices", default="0,1", help="Which slices to list")
@click.option("-p", "--planes", default="col,ind", help="Plane to draw")
@click.option("-o", "--output", default="/dev/stdout", help="Output file")
def list_holes(strips, slices, planes, output):
    '''
    Make some artwork which "obviously" shows the integration map is correct.
    '''
    slices = list(map(int,slices.split(',')))
    strips = list(range(-strips, strips+1))
    strips.reverse()
    planes = planes.split(',')
    
    d_planes = list()
    for plane in planes:
        if plane=="ind":
            pg = pcbholes.Induction()
        elif plane=="col":
            pg = pcbholes.Collection()
        else:
            raise RuntimeError(f'no such plane {plane}')

        d_strips = list()
        for strip in strips:
            d_slcs = list()
            for slc in slices:
                d_sips = list()
                for sip in [-2.5 + n*0.5 for n in range(6)]:
                    so = pg.Sip(strip, slc, sip)._asdict()
                    so['dirs'] = so['dirs'].tolist()
                    so['wirs'] = so['wirs'].tolist()
                    d_sips.append(so)
                d_slcs.append(dict(slice=slc, sips=d_sips))
            d_strips.append(dict(strip=strip, slices=d_slcs))
        d_planes.append(dict(plane=plane, strips=d_strips))
    dat = dict(planes=d_planes)
    open(output, 'wb').write(json.dumps(dat, indent=4).encode())



@cli.command("gen-wires")
@click.argument("output-file")
def gen_wires(output_file):
    '''Generate a "oneside wires" file.  Use "wirecell-util
    convert-oneside-wires" to turn into .json.bz2 file.

    columns:
        channel plane wire sx sy sz ex ey ez
    '''
    import wires
    text = wires.generate()
    open(output_file,"wb").write(text.encode('ascii'))


@cli.command("plot-one")
@click.option("-T", "--tag", default="gauss0",
             help="Tag name")
@click.option("-t", "--trigger", default=31,
             help="Trigger number")
@click.option("-a","--aspect", default=1.0,
              help="Aspect ratio")
@click.option("-o","--output",default="plot.pdf",
              help="Output file")
@click.argument("npzfile")
def plot_one(tag, trigger, aspect, output, npzfile):
    '''
    Plot waveforms of a trigger from file
    '''
    import numpy
    import matplotlib.pyplot as plt 
    fp = numpy.load(npzfile)
    a = fp[f'frame_{tag}_{trigger}']
    rows, cols = a.shape;
    print (rows,cols)

    # a = numpy.flip(a,0)
    plt.imshow(a, aspect=aspect, interpolation=None)
    plt.plot((64, 64), (0, rows-1), linewidth=0.1, color='red')
    if cols == 192:
        plt.plot((128, 128), (0, rows-1), linewidth=0.1, color='red')
    c = plt.colorbar()
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(output, bbox_inches='tight')

@cli.command("plot-many")
@click.option("-a","--aspect", default=1.0,
              help="Aspect ratio")
@click.option("-o","--output",default="plot.pdf",
              help="Output file")
@click.argument("npzfile")
def plot_many(aspect, output, npzfile):
    '''
    Plot waveforms of a trigger from file
    '''
    import numpy
    import matplotlib.pyplot as plt 
    from matplotlib.backends.backend_pdf import PdfPages
    fp = numpy.load(npzfile)
    print (list(fp.keys()))

    with PdfPages(output) as pdf:
        for k in fp.keys():
            print (k)
            if not k.startswith("frame_"):
                continue;
            a = fp[k]
            rows, cols = a.shape;
            # a = numpy.flip(a,0)
            fig, ax = plt.subplots(nrows=1, ncols=1)
            plt.imshow(a, aspect=aspect, interpolation=None)
            plt.plot((64, 64), (0, rows-1), linewidth=0.1, color='red')
            if cols == 192:
                plt.plot((128, 128), (0, rows-1), linewidth=0.1, color='red')
            c = plt.colorbar()
            plt.gca().invert_yaxis()
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()


@cli.command("activity")
@click.option("-t", "--threshold", default=5000,
             help="Threshold on the sum of values above minimum")
@click.option("-m", "--minimum", default=5,
             help="Minimum sample value to be included in sum")
@click.argument("npzfile")
@click.argument("npzout")
def activity(threshold, minimum, npzfile, npzout):
    import numpy
    fp = numpy.load(npzfile)
    arrays = dict()
    for k in fp.keys():
        if not k.startswith("frame_"):
            continue
        a = fp[k]
        c = a[:,:64]
        cn = numpy.array(c - numpy.median(c, axis=0))
        act = numpy.sum(cn[cn>5])
        if act < 5000.0:
            continue
        arrays[k] = a
        print (f'save {k}')
    numpy.savez(npzout, **arrays)
        

def main():
    cli(obj=dict())

if '__main__' == __name__:
    main()
    
