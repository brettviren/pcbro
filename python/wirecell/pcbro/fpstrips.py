#!/usr/bin/env python3
'''Functions for operating on Francesco Pietropaolo's field response
results.

'''
import os.path as osp
import numpy

def fid2pid(fid):
    '''
    Given a 3 digit numeric file ID, return (i,j) path ID where:

    - i counts [0,11] the impact position in the pitch direction
    - j counts [0,3] the position along the strip direction

    Note, for ii in [1,12] and jj in [1,4] 
          fid is originally calcualted in the FORTRAN as:
              fid = 150 + ii + 12 * (jj-1)

    But here in Python we use and return 0-counts.
    '''
    fid -= 151
    i = fid % 12 
    j = fid // 12
    return (i,j)

def parse(text):
    '''
    Given contents text of fort.XXX file, return matching 2D array
    '''
    lines = text.split('\n')
    rows = list()
    for line in lines:
        row = [float(c) for c in line.strip().split(' ') if c != '']
        if len(row) == 0:
            continue
        if len(row) != 10:
            raise ValueError(f'parse error: line {len(rows)}, length {len(row)} != 10')
        rows.append(row)
    return numpy.array(rows)

from wirecell.pcbro.util import tar_source
def parse_tar(tarfile):
    fid2arr = dict()
    for fname, text in tar_source(tarfile):
        if "fort." not in fname:
            print(f'skip unknown file: {fname}')
            continue
        print(fname)
        fid = int(osp.basename(fname)[5:8])
        if fid < 151 or fid > 198:
            print(f'skip {fname}')
            continue
        arr = parse(text)
        fid2arr[fid] = arr
    return fid2arr

def fp2wct(arr):
    '''Given an array such as produced by parse, return a new array which
    represents the application of the coordinate transform from FP's
    to WCT's convention.

    The two are related by a cyclic permutation.

    x_fp -> y_wct in the pitch direction of the induction strips
    y_fp -> z_wct along the induction strips
    z_fp -> x_wct anti drift direction

    '''
    arr = numpy.array(arr)
    wct = numpy.roll(arr[:,1:4], 1, axis=1)
    arr[:,1:4] = wct
    return arr


from matplotlib.backends.backend_pdf import PdfPages
import pylab
import matplotlib.pyplot as plt

def draw_starts(arrs, dsname, pdffile):
    '''
    '''
    arrs = list(arrs)
    xs = [arr[0][1] for arr in arrs]
    ys = [arr[0][2] for arr in arrs]
    zs = [arr[0][3] for arr in arrs]

    with PdfPages(pdffile) as pdf:
        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Y vs X starts {dsname}')
        plt.scatter(xs, ys, marker='o')
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Z vs X starts {dsname}')
        plt.scatter(xs, zs, marker='o')
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Y vs Z starts {dsname}')
        plt.scatter(zs, ys, marker='o')
        pdf.savefig(plt.gcf())
        plt.close();


def draw_paths(arrs, dsname, pdffile, frac=0.95):
    '''
    Given arrays such as from parse() make plots of paths
    '''
    arrs = list(arrs)
    frac=0.95
    start = int(frac*arrs[0].shape[0])
    pct = '%.0f%%' % ((1-frac)*100,)
    step=1

    with PdfPages(pdffile) as pdf:

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Y vs X paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,1], arr[start::step,2])
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Z vs Y paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,2], arr[start::step,3])
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'X vs Z paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,3], arr[start::step,1])
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        for arr in arrs:
            ax.scatter(arr[start::step,1], arr[start::step,2], arr[start::step,3], s=.1)
        plt.title(f'3D paths (last {pct}) {dsname}')
        pdf.savefig(plt.gcf())
        plt.close();

def draw_dataset(arr, dsname, pdffile):
    '''
    Given array such as produced by parse or coordtrans, make a plot.
    '''

    frac=0.95
    start = int(frac*arr.shape[0])
    pct = '%.0f%%' % ((1-frac)*100,)
    step = 1

    with PdfPages(pdffile) as pdf:

        #pylab.subplot(aspect='equal');

        plt.title(f'Responses {dsname}')
        for strip in range(6):
            col = strip+4
            plt.plot(arr[start::step,0], arr[start::step,col])
        pdf.savefig(plt.gcf())
        plt.close();
    
        plt.title(f'Y vs X paths {dsname}')
        plt.plot(arr[:,1], arr[:,2])
        pdf.savefig(plt.gcf())
        plt.close();

        plt.title(f'Z vs Y paths {dsname}')
        plt.plot(arr[:,2], arr[:,3])
        pdf.savefig(plt.gcf())
        plt.close();

        plt.title(f'X vs Z paths {dsname}')
        plt.plot(arr[:,3], arr[:,1])
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(arr[start::step,1], arr[start::step,2], arr[start::step,3], s=1)
        plt.title(f'3D paths (last {pct}) {dsname}')
        pdf.savefig(plt.gcf())
        plt.close();
                        
