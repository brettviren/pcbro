'''
Main CLI to moo
'''
import os
import os.path as osp
import sys
import json
import click
from wirecell import units
import numpy
import zipfile

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


@cli.command("fpstrips-fp-npz")
@click.argument("zipname")
@click.argument("npzname")
def fpstrips_fp_npz(zipname, npzname):
    '''Rewrite zip of fort.NNN files to faster FP-style NPZ.

    No processing is done.  Result is two 3D arrays of shapes:

    col: (12*6, 10, many)
    ind: (12*4, 10, many)

    The first index spans the .NNN ID number and order.
    The second index spans 10 columns (t,x,y,z,w0,w1,w2,w3,w4,w5).
    The third spans number of samples and differs in general between the two.

    '''
    from .fpstrips import fpzip2arrs
    zf = zipfile.ZipFile(zipname, 'r')
    arrs = fpzip2arrs(zf)
    numpy.savez(npzname, **arrs)


@cli.command("fpstrips-draw-fp")
@click.argument("npzname")
@click.argument("pdfname")
def fpstrips_draw_fp(npzname, pdfname):
    '''
    Make some drawings from the untouched npz file
    '''
    from .fpstrips import draw_fp
    arrs = numpy.load(npzname)
    draw_fp(arrs, pdfname)


@cli.command("fpstrips-wct-npz")
@click.argument("fpnpz")
@click.argument("wctnpz")
def fpstrips_wct_npz(fpnpz, wctnpz):
    '''
    Convert FP NPZ file to WCT NPZ file
    '''
    from .fpstrips import fp2wct
    fp = numpy.load(fpnpz)
    wct = fp2wct(fp)
    numpy.savez(wctnpz, **wct)

@cli.command("convert-fpstrips")
@click.option("--tstart", default="0",
              help="Set time start (use units eg 100*us).")
@click.option("--origin", default="10.0*cm",
              help="Set drift origin (give units, eg '10*cm').")
@click.option("--period", default="100*ns",
              help="Set sample period time (use units eg 0.1*us).")
@click.option("--speed", default="1.6*mm/us",
              help="Set nominal drift speed (give untis, eg '1.6*mm/us').")
@click.option("--pitch", type=str, default="5*mm",
              help="The pitch for the new response plane")
@click.option("--normalization", default=0.0,
              help="Set normalization: 0:none, <0:electrons, >0:multiplicative scale.  def=0")
@click.option("--zero-wire-locs", default=[0.0,0.0,0.0], nargs=3, type=float,
              help="Set location of zero wires.  def: 0 0 0")
@click.argument("filename")
@click.argument("output")
def convert_fpstrips(tstart, origin, period, speed, pitch,
                     normalization, zero_wire_locs,
                     filename, output):
    '''
    Convert FP field response data files to WCT format
    '''
    # fr level
    origin = eval(origin, units.__dict__)
    tstart = eval(tstart, units.__dict__)
    period = eval(period, units.__dict__)
    speed = eval(speed, units.__dict__)

    # pr level
    pitch = eval(pitch, units.__dict__)

    import wirecell.sigproc.response.persist as per
    from wirecell.sigproc.response.schema import (
        FieldResponse, PlaneResponse)
    from .fpstrips import fpzip2arrs, fp2wct, arrs2pr
    if filename.endswith(".zip"):
        zf = zipfile.ZipFile(filename, 'r')
        fp = fpzip2arrs(zf)
        wct = fp2wct(fp)
    elif filename.endswith(".npz"):
        arrs = numpy.load(filename)
        if arrs['col'].shape[0] > 12: # FP array
            wct = fp2wct(arrs)
        else:                   # WCT array
            wct = arrs
    else:
        print(f"Unknown data file: {filename}")
    pathresp = arrs2pr(wct, pitch)

    anti_drift_axis = (1.0, 0.0, 0.0)

    planes = [
        PlaneResponse(pathresp['ind'], 0, zero_wire_locs[0], pitch),
        PlaneResponse(pathresp['ind'], 1, zero_wire_locs[1], pitch),
        PlaneResponse(pathresp['col'], 2, zero_wire_locs[2], pitch),
    ]
    fr = FieldResponse(planes, anti_drift_axis,
                       origin, tstart, period, speed)
    per.dump(output, fr)


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

@cli.command("evd2d")
@click.option("--baseline-subtract", type=click.Choice(['median','']), default='',
             help="Apply baseline subtraction method")
@click.option("-T", "--tag", default="",
             help="Tag name")
@click.option("-t", "--trigger", default=31,
             help="Trigger number")
@click.option("-a","--aspect", default="auto", type=str,
              help="Aspect ratio")
@click.option("--title", default="Signals",
              help="Set name for unit of color scale")
@click.option("--color-range", default=None,
              help="Set color range as 'min,max' or 'min,center,max' list of numbers, default is full range")
@click.option("--color-unit", default="ionization electrons",
              help="Set name for unit of color scale")
@click.option("--color-map", default="bwr",
              help="Set color map name")
@click.option("--cnames", default="collection,induction",
              help="Comma-separated list channel group names")
@click.option("--channels", default="0:64,64:128",
              help="Colon-comma-separated list of channels to include eg '0:50,64:110'")
@click.option("--tshift", default=0, type=int,
              help="Shift data this many ticks")
@click.option("--ticks", default="0:600",
              help="Colon-separated range of ticks")
@click.option("--mask-min", default=None,
              help="Mask any values less than this value, if given")
@click.option("-o","--output",default="plot.pdf",
              help="Output file")
@click.argument("npzfile")
def evd2d(baseline_subtract, tag, trigger, aspect,
          title, color_range, color_unit, color_map,
          cnames, channels, tshift, ticks, mask_min,
          output, npzfile):
    '''
    Plot waveforms of a trigger from file
    '''
    title = title.format(**locals())

    import numpy
    import matplotlib.pyplot as plt 
    import matplotlib as mpl
    fp = numpy.load(npzfile)
    a = fp[f'frame_{tag}_{trigger}']

    rows, cols = a.shape;
    print (rows,cols)

    cnames = cnames.split(',')

    if baseline_subtract == 'median':
        a = a - numpy.median(a, axis=0)

    if color_range is None:
        color_range = [numpy.min(a), numpy.max(a)]
    else:
        color_range = [float(v) for v in color_range.split(',')]

    Normer = mpl.colors.TwoSlopeNorm
    if len(color_range) == 2:
        color_range.insert(1, 0.5*numpy.sum(color_range))
    norm = Normer(vmin=color_range[0],
                  vcenter=color_range[1],
                  vmax=color_range[2])

    if mask_min is not None:
        mask_min = float(mask_min)

    tt = list(map(int, ticks.split(":")))
    channels = [list(map(int, ss.strip().split(":"))) for ss in channels.split(",")]
    nplanes = len(channels)
    fig, axes = plt.subplots(1, nplanes, sharey=True, figsize=(10.5, 8.0))
    for pind in range(nplanes):
        cc = channels[pind]
        ax = axes[pind]
        sa = a[tt[0]-tshift:tt[1]-tshift, cc[0]:cc[1]]
        if mask_min is not None:
            sa = numpy.ma.masked_where(sa <= mask_min, sa)
        im = ax.imshow(sa, cmap=color_map, aspect=aspect, interpolation='none',
                       norm=norm, extent=[cc[0],cc[1],tt[1],tt[0]])
        ax.set_xlabel(f'{cnames[pind]} channels [IDs]')
        # ax.set_xticks
    axes[0].set_ylabel('sample period [count]')
    c = fig.colorbar(im)
    c.set_label(color_unit)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.suptitle(title, fontsize=14)
    fig.subplots_adjust(top=0.95)
    plt.savefig(output, bbox_inches='tight')


@cli.command("plot-one")
@click.option("--baseline-subtract", type=click.Choice(['median','']), default='',
             help="Apply baseline subtraction method")
@click.option("-T", "--tag", default="gauss0",
             help="Tag name")
@click.option("-t", "--trigger", default=31,
             help="Trigger number")
@click.option("-a","--aspect", default="1.0", type=str,
              help="Aspect ratio")
@click.option("-o","--output",default="plot.pdf",
              help="Output file")
@click.argument("npzfile")
def plot_one(baseline_subtract, tag, trigger, aspect, output, npzfile):
    '''
    Plot waveforms of a trigger from file
    '''
    import numpy
    import matplotlib.pyplot as plt 
    fp = numpy.load(npzfile)
    a = fp[f'frame_{tag}_{trigger}']
    rows, cols = a.shape;
    print (rows,cols)

    if baseline_subtract == 'median':
        a = a - numpy.median(a, axis=0)

    # a = numpy.flip(a,0)
    plt.imshow(a, aspect=aspect, interpolation='none')
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
    
