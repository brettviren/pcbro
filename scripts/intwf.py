#!/usr/bin/env python3
'''
Make plots showing integrated waveforms for 50-L data/sim
'''

import numpy
import matplotlib.pyplot as plt

def load_array(fname, key):
    return numpy.load(fname)[key]

def plane_totals(bychan):
    return [numpy.sum(bychan[s:s+64]) for s in [0,64,128]]

def plotit(raw, sig):
    fig, ax = plt.subplots(nrows=2, ncols=2, sharex=True)

    # raw

    #bl = numpy.abs(raw - numpy.median(raw, axis=0))
    bl = numpy.copy(raw)
    # perfect bl subtraction
    bl[:,:64] += -4095*(200/2000)
    bl[:,64:] += -4095*(900/2000)

    im = ax[0,0].imshow(bl, interpolation='none',aspect='auto')
    fig.colorbar(im, ax=ax[0,0])
    ax[0,0].set_title("raw [perfect bl-sub ADC]")

    rsum = numpy.sum(bl, axis=0)
    rtots = ["%.1e"%t for t in plane_totals(rsum)]
    ax[1,0].plot(rsum)
    #ax[1,0].set_title(f'raw ADC, bl-subtracted sum')
    ax[1,0].set_xlabel(', '.join(rtots))

    # sig

    im = ax[0,1].imshow(sig, interpolation='none',aspect='auto')
    fig.colorbar(im, ax=ax[0,1])
    ax[0,1].set_title("signal [electrons]")

    ssum = numpy.sum(sig, axis=0)
    stots = ["%.1e"%t for t in plane_totals(ssum)]
    ax[1,1].plot(ssum)
    #ax[1,1].set_title(f'signal')
    ax[1,1].set_xlabel(', '.join(stots))
    plt.tight_layout()

import click
@click.group()
def cli():
    pass

@cli.command("plot")
@click.option("-T", "--title", type=str, default=None)
@click.option("-t", "--trigger", type=int, default=0)
@click.option("-r", "--raw", type=str)
@click.option("-s", "--sig", type=str)
@click.argument("output")
def plot(title, trigger, raw, sig, output):
    if not title:
        title="Trigger {trigger}"
    title = title.format(**locals())

    plotit(load_array(raw, f'frame_orig0_{trigger}'),
           load_array(sig, f'frame_gauss0_{trigger}'))
    fig = plt.gcf()
    st = fig.suptitle(title, fontsize='x-large')
    st.set_y(0.95)
    fig.subplots_adjust(top=0.85)
    plt.savefig(output)

if '__main__' == __name__:
    cli()
