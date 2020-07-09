'''
Main CLI to moo
'''
import os
import sys
import json
import click

@click.group()
@click.pass_context
def cli(ctx):
    '''
    wirecell-pcbro command line interface
    '''
    ctx.ensure_object(dict)

@cli.command("gen-wires")
@click.argument("output-file")
def gen_wires(output_file):
    '''Generate a "oneside wires" file.  Use "wirecell-util
    convert-oneside-wires" to turn into .json.bz2 file.

    columns:
        channel plane wire sx sy sz ex ey ez
    '''
    # 320mm x 320mm active area with 64x64 strips.  Strip pitch is
    # 5mm.  1.25mm hole at 2mm hole-pitch, 2.5mm hole at 3.33 mm
    # hole-pitch.  A collection strip has constant hole pattern.
    # Induction strip is half small-hole, half large-hole.
    pitch = 0.5                 # cm, strip pitch
    

    # "physical" channels match strips and are:
    # - 1-64 for collection
    # - 65-128 for induction 1
    # - 129-192 for duplicate induction 2
    print("warning: using ideal wire spacing")
    lines = list()
    
    # In Z vs Y space the detector has 4 unique quadrants (ignoring
    # some edge details)
    # (+Y, +Z) : large holes (large col chan nums, large ind chan nums)
    # (-Y, +Z) : large holes (large col chan nums, small ind chan nums)
    # (+Y, -Z) : small holes (small col chan nums, large ind chan nums)
    # (-Y, -Z) : small holes (small col chan nums, small ind chan nums)
    

    # A first inducton strip runs parallel to Z axis.  Small holes are
    # Z<0, big holds Z>0.  Strips counted from most negative to most
    # positive Y.  A strip boundary between two middle strips is at
    # Y=0.
    plane=0
    sx = ex = +0.1              # cm, bogus value
    sz = -32*pitch
    ez = +32*pitch
    sy = ey = -32*pitch + 0.5*pitch
    for iwire in range(64,128):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch
        ey += pitch
        
    # A second induction plane is identically overlapping the first
    # and has "virtual" channels starting just after the first
    # induction plane.  Data for this plane is identical for first
    # induction but may have a different field response.
    plane=1
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = +0.1              # cm, and totally bogus
    sz = -32*pitch
    ez = +32*pitch
    sy = ey = -32*pitch + 0.5*pitch
    for iwire in range(128,192):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch
        ey += pitch

    # A single collection plane has strips parallel to the Y-axis.
    # Strips are counted from most-negative to most-positive Z.  First
    # 32 channels (Z<0) have small holes, second 32 channels (Z>0)
    # have large holes.
    plane=2                     # collection
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = -0.1              # cm, and totally bogus
    sy = -32*pitch
    ey = +32*pitch
    sz = ez = -32*pitch + 0.5*pitch
    for iwire in range(0,64):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sz += pitch
        ez += pitch

    text = '\n'.join(lines)
    text += '\n'
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
    
