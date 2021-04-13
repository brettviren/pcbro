#!/usr/bin/env python
'''
Given a 50L numpy file, find per-channel peak, shift wf to make it
center, form average wf.

Like best used when activity is from a lone muon crossing the
channels.
'''

import sys
import click
import numpy
import matplotlib.pyplot as plt

def avgwf(bled, thresh_sigma=5, offset=0):
    nticks = bled.shape[0]

    res_avg = numpy.zeros((nticks*2,))
    res_2d = numpy.zeros((nticks*2, bled.shape[1]))
    count = 0

    peak_inds = numpy.argmax(bled, axis=0)
    for oind, pind in enumerate(peak_inds):
        pval = bled[pind, oind]
        tmp = numpy.copy(bled[:,oind])
        # quick and dirty ignoring of signal.
        tmp[pind-10:pind+10] = 0
        stddev = numpy.std(tmp)
        thresh = thresh_sigma * stddev
        pwf = bled[:,oind]
        off = nticks-pind+offset
        okay=True
        if pind == 0:
            okay=False
        if pval < thresh:
            okay=False
        #print(f'{count}: {nticks} {pind} {off} {pval:.1f} {thresh:.3f} {okay}')
        if not okay:
            continue
        res_2d[off:off+nticks, oind] = pwf
        res_avg[off:off+nticks] += pwf
        count += 1
    if count > 0:
        res_avg /= count
    return (res_avg[nticks//2: nticks//2 + nticks],
            res_2d[nticks//2: nticks//2 + nticks,:])

def load(fname, arrname):
    fp = numpy.load(fname)
    if not arrname:
        arrname = list(fp.keys())[0]
    raw = numpy.load(fname)[arrname]
    med = numpy.median(raw, axis=0)
    bled = raw - med
    col=bled[:,0:64]
    ind=numpy.abs(bled[:,64:128])
    print(f'loaded {fname}:{arrname} {raw.shape}')
    return col,ind

@click.group()
def cli():
    pass

@cli.command()
@click.option("-a", "--array", type=str)
@click.option("-o", "--output", type=str, default="avgwf.png")
@click.option("--offset", type=int, default=0)
@click.argument("infile")
def plot(array, output, offset, infile):
    raw = load(infile, array)
    avgs = [avgwf(raw[0]), avgwf(raw[1])]
    fig, axes = plt.subplots(nrows=4, ncols=2)
    for ind, nam in enumerate(["col", "ind"]):
        avg, avg2d = avgs[ind]

        axes[0,ind].imshow(raw[ind].T, aspect='auto')
        axes[0,ind].set_xlim(0, 600.0)
        axes[1,ind].imshow(avg2d.T, aspect='auto')
        axes[1,ind].set_xlim(0, 600.0)

        axes[2,ind].semilogy(avg)
        axes[2,ind].grid()
        axes[2,ind].set_ylim(0.1, 200.0)
        axes[2,ind].set_title(f"{nam} avg")
        axes[2,ind].set_xlim(0, 600.0)

        nticks = avg.shape[0]
        axes[3,ind].plot(avg[nticks//2-20:nticks//2+20])
        axes[3,ind].grid()
        axes[3,ind].set_ylim(0.0, 200.0)
        axes[3,ind].set_title(f"{nam} avg (zoom)")
    plt.tight_layout()
    plt.savefig(output)


if '__main__' == __name__:
    cli()
