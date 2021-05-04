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
import tarfile

import wirecell.pcbro.garfield as pcbgf
import wirecell.pcbro.draw as pcbdraw
import wirecell.pcbro.holes as pcbholes
import wirecell.sigproc.garfield as wctgf

from wirecell.util.fileio import load as source_loader
# def sourceme(source):
#     '''
#     Convert a tar file or directory path into a source
#     '''
#     if osp.splitext(source)[1] in ['.tar', '.tgz']:
#         return pcbgf.tar_source(source)
#     if osp.isdir(source):
#         return pcbgf.dir_source(source, ['ind'])
#     raise ValueError(f"Unsupported source: {source}")

@click.group()
@click.pass_context
def cli(ctx):
    '''
    wirecell-pcbro command line interface
    '''
    ctx.ensure_object(dict)


@cli.command("fpstrips-fp-npz")
@click.argument("infile")
@click.argument("npzname")
def fpstrips_fp_npz(infile, npzname):
    '''Rewrite zip/tar of fort.NNN files to faster FP-style NPZ.

    No processing is done.  Result is two 3D arrays of shapes:

    col: (12*6, 10, many)
    ind: (12*4, 10, many)

    The first index spans the .NNN ID number and order.
    The second index spans 10 columns (t,x,y,z,w0,w1,w2,w3,w4,w5).
    The third spans number of samples and differs in general between the two.

    '''
    from .fpstrips import fpzip2arrs

    af = source_loader(infile)
    arrs = fpzip2arrs(af)
    numpy.savez(npzname, **arrs)

@cli.command("fpstrips-trio-npz")
@click.option("--ind1", type=str, help="induction1 tar file")
@click.option("--ind2", type=str, help="induction2 tar file")
@click.option("--col", type=str, help="collection tar file")
@click.argument("npzname")
def fpstrips_trio_npz(ind1, ind2, col, npzname):
    '''Rewrite zips/tars of fort.2NN files to FP-style NPZ.

    No processing beyond reformating is done.

    Each induction1/2 and collection given as a separate tar/zip.

    Each array is shape (npaths, ncolumns, nsamples)

    ncolumns are FP's 10 data columns

    '''
    from .fpstrips import fpzip2arrs

    out = dict()
    keyed = dict(ind1=ind1, ind2=ind2, col=col)
    for key,fname in keyed.items():
        af = source_loader(fname)
        arrs = fpzip2arrs(af)
        if 'ind' in arrs:
            raise ValueError("unexpected 'ind' response")
        out[key] = arrs['col']
    numpy.savez(npzname, **out)



@cli.command("draw-fp")
@click.option("-m", "--method", type=str, default='diag',
              help="Set the drawing method")
@click.option("-s","--start", default="0*us",
              help="Start time, using units")
@click.option("-o","--output", default="plot.pdf",
              help="Output file")
@click.argument("npzname")
def draw_fp(method, start, output, npzname):
    '''
    Make some drawings from the untouched npz file
    '''
    start = eval(start, units.__dict__)

    from . import fpstrips
    meth = getattr(fpstrips, f'draw_fp_{method}')

    arrs = numpy.load(npzname)
    meth(arrs, output, start=start)




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


def load_sidecar(fpfile):
    '''
    Load a JSON "sidecar" to the given fpfile.
    '''
    for ext in ('.zip', '.tar', '.tgz', '.tar.gz'):
        if fpfile.endswith(ext):
            jsonfile = fpfile.replace(ext,'.json')
            break
    dat = json.loads(open(jsonfile,'rb').read().decode())
    for p in dat['planes']:     # apply units
        for united in ('pitch','hole'):
            p[united] = eval(p[united], units.__dict__)
    return dat

@cli.command("convert-fpstrips")
@click.option("--tshift", default=0, type=int,
              help="Number of ticks to shift response values")
@click.option("--nticks", default=None, type=int,
              help="Limit total number of ticks in the response functions")
# @click.option("--tstart", default="0",
#               help="Set time start (use units eg 100*us).")
# @click.option("--origin", default="20.0*cm",
#               help="Set drift origin (give units, eg '10*cm').")
# @click.option("--period", default="100*ns",
#               help="Set sample period time (use units eg 0.1*us).")
# @click.option("--speed", default="1.55*mm/us",
#               help="Set nominal drift speed (give untis, eg '1.6*mm/us').")
# @click.option("--pitch", type=str, default="5*mm,5*mm,5*mm",
#               help="The pitches for the new response planes")
@click.option("--location", default="3.2*mm,3.2*mm,0*mm", 
              help="Set location of planes")
@click.argument("filename")
@click.argument("output")
def convert_fpstrips(tshift, nticks, location, filename, output):
    '''
    Convert FP field response data files to WCT format
    '''
    meta = load_sidecar(filename)
    name = meta['name']
    pitchpp = {p['name']:p['pitch'] for p in meta['planes']}
    plns = [p['name'] for p in meta['planes']]
    if len(plns) == 2:
        plns = tuple([plns[0]] + list(plns))
    print(f'loading {name}')


    location = [eval(l, units.__dict__) for l in location.split(",")]

    import wirecell.sigproc.response.persist as per
    from wirecell.sigproc.response.schema import (
        FieldResponse, PlaneResponse)
    from .fpstrips import fpzip2arrs, fp2wct, arrs2pr, fp2meta

    rebin = 20

    if osp.splitext(filename)[-1] in (".zip",".tar",".tgz"):
        print("Got FP archive")
        af = source_loader(filename)
        fparrs = fpzip2arrs(af)
        wct = fp2wct(fparrs, rebin=rebin, tshift=tshift, nticks=nticks)
    elif filename.endswith(".npz"):
        fparrs = numpy.load(filename)
        if fparrs['col'].shape[0] > 12: # FP array
            print("Got FP NPZ")
            wct = fp2wct(fparrs, rebin=rebin, tshift=tshift, nticks=nticks)
        else:                   # WCT array
            raise ValueError("NPZ does not look like FP variety")
            # print("Got WCT NPZ")
            # wct = arrs
    else:
        raise ValueError(f"Unknown data file: {filename}")

    meta = fp2meta(fparrs)
    print(f'meta: {meta}')
    origin = meta['origin']
    speed = meta['speed']
    period = meta['period']*rebin
    tstart = meta['tstart']
    
    anti_drift_axis = (1.0, 0.0, 0.0)

    pathresp = arrs2pr(wct, pitchpp)

    planes = [
        PlaneResponse(pathresp[nam], num, location[num], pitchpp[nam])
        for num, nam in enumerate(plns)]

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
@click.option("-f", "--format", default="json.bz2",
              type=click.Choice(['json', 'json.gz', 'json.bz2']),
              help="Set output file format")
@click.option("-b", "--basename", default="pcbro-response",
              help="Set basename for output files")
@click.argument("garfield-fileset")
def convert_garfield(origin, speed, normalization, 
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


    ripem = gar.Ripem(source_loader(garfield_fileset))
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
    source = source_loader(source, pattern="*.dat")
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
@click.option("-d", "--detector", default="50l",
              type=click.Choice(["50l"]),
              #type=click.Choice(["50l","ref3"]),
              help="Set the detector")
@click.option("-p", "--pitch", default="5*mm",
              help="Set pitch of planes")
@click.argument("output-file")
def gen_wires(detector, pitch, output_file):
    '''Generate a "oneside wires" file.  Use "wirecell-util
    convert-oneside-wires" to turn into .json.bz2 file.

    columns:
        channel plane wire sx sy sz ex ey ez
    '''
    import wirecell.pcbro.wires as wires

    if "," in pitch:
        pitch = pitch.split(",")
    else:
        pitch = [pitch]*3
    pitch = [eval(p, units.__dict__) for p in pitch]

    meth = getattr(wires, "generate_" + detector)
    text = meth(pitch)
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
        trignum = int(k.split("_")[-1])
        if trignum >= 49:
            continue

        a = fp[k]
        c = a[:,:64]
        cn = numpy.array(c - numpy.median(c, axis=0))
        col = cn[:,0:32]
        tcol = numpy.sum(col[col>minimum])
        if tcol < threshold:
            continue
        ind = cn[:,32:64]
        tind = numpy.sum(ind[ind>minimum])
        if tind < threshold:
            continue
        arrays[k] = a
        print (f'save {k}')
    numpy.savez(npzout, **arrays)
        
@cli.command("npzjoin")
@click.option("-t","--tag", default="gauss0",
              help="Which tag to select")
@click.option("-o","--output", default="joined.npz",
              type=click.Path(exists=False),
              help="Give output NPZ file name")
@click.argument("npzfiles", nargs=-1)
def npzjoin(output, tag, npzfiles):
    '''Join frames across set of npz files to one.  Rewrite trigger
    numbers.
    '''
    if os.path.exists(output):
        raise RuntimeError(f'will not overwrite existing file: {output}')

    want = f"frame_{tag}_"
    newtrig=0
    arrays = dict()
    for npzfile in npzfiles:
        print(npzfile)
        ts = os.path.splitext(npzfile)[0].split("-")[-1]
        ts = ts[:-2]
        fp = numpy.load(npzfile)
        for k,arr in fp.items():
            if not k.startswith(want):
                continue
            _, tag,trig = k.split('_')
            arrays[f'frame_{tag}_{ts}{newtrig:02d}'] = arr
            newtrig += 1
    numpy.savez(output, **arrays)
    

def main():
    cli(obj=dict())

if '__main__' == __name__:
    main()
    
