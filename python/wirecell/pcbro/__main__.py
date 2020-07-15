'''
Main CLI to moo
'''
import os
import os.path as osp
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

@cli.command("convert-garfield")
@click.argument("garfield-fileset")
@click.argument("wirecell-field-response-file")
def convert_garfield(garfield_fileset, wirecell_field_response_file):
    '''
    Produce a WCT field file from tarfile of Garfield output text files.

    See also same subcommand from wirecell-sigproc
    '''
    import wirecell.pcbro.garfield as pcbgf
    pcbgf.load(garfield_fileset)    

@cli.command("convert-garfield-one")
@click.option("-o","--output",default=None, help="Output .npz file")
@click.argument("datfile")
def convert_garfield_one(output, datfile):
    '''
    Convert one Garfield .dat file to a .npz file
    '''
    import wirecell.pcbro.garfield as pcbgf
    if not output:
        output = os.path.splitext(os.path.basename(datfile))[0] + ".npz"
    pcbgf.dat2npz(datfile, output)    

@cli.command("plot-garfield")
@click.option("-o","--output", default="garfield-plots.pdf", help="Output PDF file")
@click.argument("source")
def print_garfield(output, source):
    import wirecell.pcbro.garfield as pcbgf
    if osp.splitext(source) in ['.tar', '.tgz']:
        source = pcbgf.tar_source(source)
    elif osp.isdir(source):
        source = pcbgf.dir_source(source, ['ind'])
    pcbgf.plots(source, output)

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
    
