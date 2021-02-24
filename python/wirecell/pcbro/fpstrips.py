#!/usr/bin/env python3
'''Functions for operating on Francesco Pietropaolo's field response
results.

'''
import os.path as osp
import numpy
from wirecell import units

legal_fids = dict(
    ind = list(range(151, 199)),
    col = list(range(201, 273)))


def pid2fid(pi, li, pl, strip=0):
    '''
    Convert path ID to "francesco" ID.

    pi in [0,11] counts bin from negative strip edge
    li in [0,3] counts along strip length
    '''
    assert pl in ('ind', 'col')
    if pl == 'ind':
        fid = 150 + pi+1 + 12*li
    else:
        if strip == 0:
            fid = 200 + pi+1 + 12*li
        elif strip in (1,3):
            fid = 200 + (12-pi)+1 + 12*li
        else:                   # strip 2
            fid = 200 + (12-pi)+1 + 12*(6-li)
    assert fid in legal_fids[pl]
    return fid

def fid2pid(fid):
    '''
    Given a 3 digit numeric file ID, return (i,j) path ID and plane name where:

    - i counts [0,11] the impact position in the pitch direction
    - j counts [0,3] the position along the strip direction for fid<200 and [0,5] for fid>200

    Note, for ii in [1,12] and jj in [1,4] 
          fid is originally calcualted in the FORTRAN as:
              fid = 150 + ii + 12 * (jj-1)

    But here in Python we use and return 0-counts.
    '''
    ifid = int(fid)
    if ifid < 200:
        zfid = ifid - 151
        pl = 'ind'
    else:
        zfid = ifid - 201
        pl = 'col'
    if ifid not in legal_fids[pl]:
        raise ValueError(f'illegal fid: {ifid}')

    i = zfid % 12 
    j = zfid // 12
    return (i,j), pl

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
    all_legal = legal_fids['ind'] + legal_fids['col']

    for fname, text in tar_source(tarfile):
        if "fort." not in fname:
            print(f'skip unknown file: {fname}')
            continue
        print(fname)
        fid = int(osp.basename(fname)[5:8])
        if fid not in all_legal:
            print(f'skip {fname}')
            continue
        arr = parse(text)
        fid2arr[fid] = arr
        print(fname, fid, arr.shape)
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
import matplotlib as mpl

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

def plane_response(array, planeid, location, pitch):
    '''Convert array from fids2array into a WCT plane response schema object.

    The array is assumed to be 11 strips and in each strip 12 impact positions.
    
    The 6 impact positions on the negative side of each strip are
    used.  Those on the positive side are ignored (they are related by
    symmetry) but their rows must exist.

    The remainder are as defined in PlaneResponse

    '''
    from wirecell.sigproc.response.schema import PlaneResponse, PathResponse
    nimps, nticks = array.shape
    nstrips = 1 + 2*5
    nimpsperstrip = 6
    paths = list()
    # count strips from most negative on up
    for istrip in range(nstrips):
        for rip in range(6):
            ind = istrip*12 + rip
            pitchpos = (istrip - 5)*pitch - rip*(pitch/5)
            path = PathResponse(array[ind], pitchpos, wirepos=0)
            paths.append(path)
    pr = PlaneResponse(paths, planeid, location, pitch)
    return pr

def fids2array(fid2arrs, pl, longs=(0,1,2,3), reflect=False):
    '''Return 2D response as function of impact vs tick in WCT form

    It performs average along the strip length using the longitudinal
    position indices given by longs.

    Result is 11x12 impact positions X nticks 2D array for 11 strips =
    0+/-5 and 12 impacts per strip.  

    The response is assumedin FP's units: 

        The current is given in electron/microseconds and is the one
        induced by 10^3 electrons

    '''
    assert pl in ('ind', 'col')

    # we will MULTIPLY this scale so we get in WCT system of units for
    # current induced by one electron.
    scale = 1e-3 * units.eplus / units.microsecond

    assert longs

    nlong_max = 4
    if pl == 'col':
        nlong_max = 6
    assert len(longs) <= nlong_max
    npaths_expect = nlong_max*12

    npaths = len(fid2arrs)
    assert npaths == nlong_max*12
    nticks = max([a.shape[0] for a in fid2arrs.values()])
    assert all([a.shape[1]==10 for a in fid2arrs.values()])

    # FP data comes in 5ns bins and WCT works with 100ns This is
    # current so we sum up 20 bins.  To do this we pad out to nearest
    # factor of 20 ticks.
    nticks = nticks + (20-nticks%20)
    nticks_final = nticks//20
    assert nticks%20 == 0

    # We want current over 20 bins = (total charge)/(total time) = sum(I_i*dt)/sum(dt) = sum(I_i)/20
    scale /= 20.0

    nimps = 11 * 12
    block = numpy.zeros((nimps, nticks_final))

    nlongs = len(longs)
    for li in longs:

        # negative side of strip, postive strips
        for pi in range(6):     
            fid = str(pid2fid(pi,li, pl))
            arr = fid2arrs[fid]

            for istrip in range(6):
                imp = (istrip+5)*12 + pi
                col = 4 + istrip
                wf = numpy.array(arr[:,col])
                wf.resize(nticks, refcheck=False)
                wf = numpy.sum(wf.reshape(-1,20), axis=1)
                block[imp,:] += wf

        # reflect positive side to get negative strips
        for pi in range(6,12):  
            fid = str(pid2fid(pi,li, pl))
            arr = fid2arrs[fid]

            for istrip in range(1, 6):
                imp = (5-istrip)*12 + (11-pi)
                col = 4 + istrip
                wf = numpy.array(arr[:,col])
                wf.resize(nticks, refcheck=False)
                wf = numpy.sum(wf.reshape(-1,20), axis=1)
                block[imp,:] += wf

    block *= scale/nlongs
    if reflect:
        block += numpy.flip(block, axis=0)
    return block


def raw_to_splt(fid2arrs):
    '''Convert fid-keyed file data to a block of responses in a 4D block.

    Block layout is (strip, pitch, long, tick).

    pitch and long are indicies in pitch (across) or long (along)
    strip direction.  Assumed: pitch in [0,11], long in [0,3] for 1xx
    fids and [0,5] for 2xx fids.

    Except for zero end padding no data is changed.

    Implicit assumption is that every response sample is time-aligned.

    '''

    nstrips = 6
    nimps = 12
    nlongs = 4
    fids = list(sorted(fid2arrs.keys()))
    if int(fids[0]) > 200:
        nlongs= 6

    nticks = max([a.shape[0] for a in fid2arrs.values()])

    #strip,pitch,long,tick
    splt = numpy.zeros((nstrips,nimps,nlongs,nticks))
    for fid in fids:
        arr = fid2arrs[fid]
        nhere = arr.shape[0]
        #print ("FID", fid, nhere)
        for istrip in range(6):
            col = 4+istrip
            (pi,li),pl = fid2pid(fid)
            #print(istrip,pi,li,nhere,col)
            splt[istrip,pi,li,:nhere] = arr[:,col]

    return splt

from wirecell.sigproc.response.plots import lg10

def draw_splt(splt, dsname, pdffile, pl):
    '''Make drawings from raw SPLT array for given plane pl in {'ind','col'}

    It is assumed response is in units of "electrons/microsecond" as
    produced by 1e3 electrons in 5ns ticks.

    '''
    neles = 1e3

    nticks = splt.shape[-1]
    nticks_to20 = nticks + 20 - nticks%20
    nticks_wct = nticks_to20 // 20

    spl_tot = numpy.sum(splt, axis=3)
    nlong = 4
    if pl == 'col':
        nlong=6
    spl_tflat = spl_tot.reshape(6*12*nlong)
    raw_avg = numpy.mean(splt, axis = 2).reshape(6*12,-1)

    # Put in WCT units of current
    wct_splt = splt / neles * units.eplus / units.microsecond
    # Average over 4 samples along strip 
    wct_avg = numpy.mean(splt, axis = 2) / neles * units.eplus / units.microsecond
    tmp = numpy.array(wct_avg.reshape(6*12,-1))
    tmp.resize(6*12, nticks_to20) # pad ticks to factor of 20.
    wct = numpy.mean(tmp.reshape(72,-1,20), axis=2)
    # integrate 20 * 5ns = 100 ns bins
    wct_tot = 0.1 * units.microsecond * numpy.sum(wct, axis=1)

    with PdfPages(pdffile) as pdf:

        Normer = mpl.colors.TwoSlopeNorm
        norm = Normer(vmin=numpy.min(raw_avg),
                      vcenter=0.0,
                      vmax=numpy.max(raw_avg))

        # raw
        fig = plt.figure()
        ax = fig.add_subplot(111)
        plt.title(f'Raw response')
        plt.imshow(raw_avg[:,22000:], aspect='auto',
                   interpolation='none', norm=norm)
        ax.set_xlabel(f'tick (5ns bins)')
        ax.set_ylabel('position')
        plt.colorbar()
        pdf.savefig(plt.gcf())
        plt.close();
        
        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='auto')
        plt.title(f'Integrated raw response ({dsname})')
        plt.plot(spl_tflat * 0.005 / neles)
        ax.set_xlabel(f'path index')
        ax.set_ylabel('integrated current [electrons]')
        pdf.savefig(plt.gcf())
        plt.close();

        # wct

        #toplot = lg10(wct[:,1000:]/units.picoampere)
        toplot = wct[:,1000:]/units.picoampere
        #toplot = wct[:,1000:]/(units.eplus/units.microsecond)
        norm2 = Normer(vmin=numpy.min(toplot),
                      vcenter=0.0,
                      vmax=numpy.max(toplot))

        fig = plt.figure()
        ax = fig.add_subplot(111)
        plt.title(f'Response [pA]')
        plt.imshow(toplot, aspect='auto',
                   interpolation='none', norm=norm2)
        ax.set_xlabel('tick (100ns bins)')
        ax.set_ylabel('position')
        plt.colorbar()
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='auto')
        plt.title(f'Integrated response ({dsname})')
        plt.plot(wct_tot/units.eplus)
        ax.set_xlabel('path index on a strip')
        ax.set_ylabel('integrated current [electron]')
        pdf.savefig(plt.gcf())
        plt.close();

        



def draw(fid2arrs, pl, dsname, pdffile, frac=0.95):
    '''
    Given arrays such as from parse() make plots of paths

    fids should be from given plane

    '''
    pl in ('ind', 'col')

    arrs = list(fid2arrs.values())

    frac=0.95
    start = int(frac*arrs[0].shape[0])
    coarse_start = start // 20
    pct = '%.0f%%' % ((1-frac)*100,)
    step=1

    with PdfPages(pdffile) as pdf:

        slices = [[s] for s in list(range(4))]
        slices.append(list(range(4)))
        for longs in slices:
            fig = plt.figure()
            ax = fig.add_subplot(111, aspect='auto')
            rf = fids2array(fid2arrs, pl, longs, reflect=True)  
            plt.imshow(rf[:,coarse_start:]/units.microampere, interpolation='none', aspect='auto')
            plt.colorbar()
            plt.title(f'Responses [uA] (slices {longs}) {dsname}')
            pdf.savefig(plt.gcf())
            plt.close();

            fig = plt.figure()
            ax = fig.add_subplot(111)
            tot = numpy.sum(rf, axis=1)
            plt.plot(tot/units.microampere)
            plt.title(f'Integrated current [uA] (slices {longs}) {dsname}')
            pdf.savefig(plt.gcf())
            plt.close();

        for fid, arr in fid2arrs.items():
            fig = plt.figure()
            pid,pl = fid2pid(fid)
            ax = fig.add_subplot(111)
            plt.title(f'Responses for pos {fid}={pid}')
            for istrip in range(6):
                col = 4+istrip
                plt.plot(arr[start:,0], arr[start:,col])
            pdf.savefig(plt.gcf())
            plt.close();

        xstart = list()
        ystart = list()
        zstart = list()
        idtext = list()
        for fid, arr in fid2arrs.items():
            xstart.append(arr[0,1])
            ystart.append(arr[0,2])
            zstart.append(arr[0,3])
            pid,pl = fid2pid(fid)
            idtext.append(f'{fid}={pid}')

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Y vs X starts {dsname}')
        plt.scatter(xstart, ystart)
        for x,y,s in zip(xstart, ystart, idtext):
            plt.text(x,y,s, rotation=30)
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Z vs Y starts {dsname}')
        plt.scatter(ystart, zstart)
        for z,y,s in zip(zstart, ystart, idtext):
            plt.text(y,z,s, rotation=30)
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'X vs Z starts {dsname}')
        plt.scatter(zstart, xstart)
        for z,x,s in zip(zstart, xstart, idtext):
            plt.text(z,x,s, rotation=30)
        pdf.savefig(plt.gcf())
        plt.close();

        ## paths

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Y vs X paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,1], arr[start::step,2])
        plt.scatter(xstart, ystart)
        pdf.savefig(plt.gcf())
        plt.close();
        
        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'Z vs Y paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,2], arr[start::step,3])
        plt.scatter(ystart, zstart)
        pdf.savefig(plt.gcf())
        plt.close();

        fig = plt.figure()
        ax = fig.add_subplot(111, aspect='equal')
        plt.title(f'X vs Z paths {dsname}')
        for arr in arrs:
            plt.plot(arr[start::step,3], arr[start::step,1])
        plt.scatter(zstart, xstart)
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
                        
