#!/usr/bin/env python3
'''Functions for operating on Francesco Pietropaolo's field response
results.

'''
import os.path as osp
import numpy
from wirecell import units

from matplotlib.backends.backend_pdf import PdfPages
import pylab
import matplotlib.pyplot as plt
import matplotlib as mpl

# from wirecell.sigproc.response.plots import lg10
def lg10(arr, eps = 1e-5):
    shape = arr.shape
    arr = numpy.array(arr).reshape(shape[0]*shape[1])
    arr[numpy.logical_and(arr < eps, arr > -eps)] = 0.0
    pos = arr>eps
    neg = arr<-eps
    arr[pos] = numpy.log10(arr[pos]/eps)
    arr[neg] = -numpy.log10(-arr[neg]/eps)
    return arr.reshape(shape)

legal_fids = dict(
    ind = list(range(151, 199)),
    col = list(range(201, 273)))

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



def fpzip2arrs(zfobj):
    '''Given a zipfile obj full of FP fort.NNN files, such as downloaded
    from dropbox, return corresponding numpy arrays with no processing

    eg, pass in 

    >>> zfobj = zipfile.ZipFile('dv-2000v.zip', 'r')

    return dict keyed by ("col", "ind") with values of 3D array with
    layout that spans dimensions of:

        (<fid>, <column>, <sample>) 

    Shapes are:

        col: (6x12, 10, many1)
        ind: (4x12, 10, many2)

    The many1 and many2 may not be equal.  Each 3D array has <sample>
    dimension zero padded to fit maximum path.

    '''
    all_legal = legal_fids['ind'] + legal_fids['col']

    arrs = list()

    for fname in zfobj.namelist():
        if len(fname) != 8:
            print(f"skipping {fname}")
            continue
        fort,fid = fname.split('.')
        fid = int(fid)
        if fid not in all_legal:
            print(f"skipping {fname}")
            continue

        with zfobj.open(fname) as fp:
            text = fp.read().decode()
            arr = parse(text)
            arrs.append((fid, arr))

    def reg(alst):
        '''Regularize list of N 2D arrays of shape (many, 10) to 3D array of
        shape (N,10,max(many))
        '''
        nfids = len(alst)
        nsamps = max([a.shape[0] for a in alst])
        block = numpy.zeros((nfids, 10, nsamps))
        for i,a in enumerate(alst):
            n = a.shape[0]
            block[i,:,:n] = a.T
        return block
        
    # shape: (12*6 or 12*4, 10, many)
    return dict(col=reg([a[1] for a in sorted(arrs) if a[0] > 200]),
                ind=reg([a[1] for a in sorted(arrs) if a[0] < 200]))
    
def fp2wct(arrs, rebin=20):
    '''Convert dict of FP arrays to WCT equivalents

    The "arrs" dict is as returned fpzip2arrs() into WCT equivalent.

    The array values in the dict are of shapes:

        col: (72, 10, many)
        ind: (48, 10, many)

    The ordering of the 72 or 48 paths are as-provided by FP.  They
    are assumed to be pitch-major ordered.

    Return dict of same keys with each array reduced in size as:

        col: (12, 10, fewer)
        ind: (12, 10, fewer)

    This will:
    - scale the 10 fort.NNN values to WCT units
    - rebin the samples (many->fewer) periods to match WCT convention (5ns to 100ns)
    - average along strip positions for a given impact position (6x12 or 4x12 -> 12)
    - regularize impact positions (flip 12 impact positions for collection strip>0)

    '''
    ret = dict()


    for pl, arr in sorted(arrs.items()):
        nfids, ncols, nsamps = arr.shape
        assert ncols == 10

        # nfids=(nlong*npitch), pitch-major ordering

        # break out the current arrays
        curs = arr[:, 4:, :]           # (nfids, 6, many)
        print(f'{pl} input curs {curs.shape}')

        # with PdfPages(f'debug-{pl}.pdf') as pdf:
        #     print(f'{pl} write debug PDF')
        #     junk = curs.reshape(-1, 12, 6, nsamps)[0].transpose((1,0,2)).reshape(12*6,nsamps)
        #     start=int(nsamps*0.95)
        #     plt.imshow(junk[:,start:], aspect='auto',
        #                interpolation='none')
        #     pdf.savefig(plt.gcf())
        #     plt.close();

        # Reshape to pull out along-strip positions as dim 0
        curs = curs.reshape((-1, 12, 6, nsamps))
        # Average along the strip
        curs = numpy.mean(curs, axis=0)
        # now have shape: (nimps=12, nstrips=6, nsamps=many)
        print(f'{pl} after mean {curs.shape}')
        
        # FP's field calculation exploits an equivalence symmetry in
        # the strip+hole pattern for collection which is baked into
        # the results.  We undo it by "flipping" the impact positions
        # for collection strips > 0.  If we had to keep distinct the
        # positions along the strip we'd need a second flip in that
        # direction for strip 2 but the reshape+mean negates that
        if pl == 'col':
            lu = list(range(12))
            ld = list(range(12))
            ld.reverse()
            for ind in [1,2,3]:
                print(f'Swapping collection strip {ind}')
                curs[lu, ind, :] = curs[ld, ind, :]

        # Zero-pad currents out to exact multiple of rebin=20 samples
        # (nimps=12, nstrips=6, samples=mult-of-20)
        extra = nsamps%rebin
        if extra:
            nrebin = nsamps + (rebin - extra)
            newcurs = numpy.zeros((12, 6, nrebin))
            newcurs[:,:,:nsamps] = curs
            curs = newcurs

        # Integrate over each rebin period (20 for 5ns->100ns).  This
        # is *current* so we sum the amount of charge induced over
        # each small sample period assuming constant current and then
        # divide by total rebinned bin time of resulting large sample
        # period: I_j = sum(dt_i * I_i)/sum(dt_i) where sum is over i
        # in [j*rebin,(j+1)*rebin-1].  This simply the mean over each
        # rebin period.
        #
        # Pull out a dimension over each rebin period
        curs = numpy.mean(curs.reshape((12, 6, -1, curs.shape[-1]//20)), axis=2)
        # shape now (12,6,nsamps/20)

        # FP current is in units of electrons/microsecond and uses
        # 10^3 electrons as the element of drifting charge.
        norm = 1e-3 * units.eplus/units.microsecond
        curs *= norm

        # Doctor the coordintaes, first take start of every rebin
        txyz = arr[:, :4, 0::rebin]    # (nfids, 4, many/rebin)
        txyz = txyz.reshape((-1, 12, 4, txyz.shape[-1]))
        # take first among 4 or 6 along strip positions as representative.
        txyz = txyz[0]          # (12, 4, many/rebin)
        #print(f'{pl} fp {txyz.shape} coords: {txyz[:,:,0]}')
        # WCT XYZ is a cyclic permuation of FP's
        txyz[1:,:] = numpy.roll(txyz[1:,:], 1, axis=0)
        # units
        txyz[0,:] *= units.microsecond
        txyz[1:,:] *= units.millimeter
        #print(f'{pl} wc {txyz.shape} coords: {txyz[:,:,0]}')

        # rejoin and done
        # print(f'txyz:{txyz.shape}, curs:{curs.shape}')
        # shape: (12, 10, many)
        ret[pl] = numpy.concatenate((txyz, curs), axis=1)
    return ret

def arrs2pr(wct, pitch):
    '''Return dict of PlathResponse lists derived from from "wct" type array as from fp2wct()

    Each array is assumed to be shaped as (12, 10, nsamples).
    '''
    from wirecell.sigproc.response.schema import PathResponse

    ret = dict()
    for pl, arr in wct.items():

        print(f'{pl} input shape {arr.shape}')

        with PdfPages(f'debug-{pl}.pdf') as pdf:
            print(f'{pl} write debug PDF')
            junk = arr[:, 4:, :].transpose((1,0,2)).reshape(12*6,-1)
            plt.imshow(junk, aspect='auto',
                       interpolation='none')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();

        twelve, ten, nticks = arr.shape
        assert ten == 10
        assert twelve == 12

        paths = list()

        # map lower impact positions of FP strips to lower impact
        # positions of lower (0 and negative) WCT strips.
        for pi in range(6,12):  # FP impact positions
            pia = arr[pi]       # shape: (10, nticks)
            assert pia.shape[0] == 10

            # count strips in FP table
            for istrip in range(6):
                # column in FP table
                col = 4 + istrip
                resp = pia[col]
                pitchpos = (-istrip - (pi-6)/10.0)*pitch
                pr = PathResponse(resp, pitchpos, wirepos=0)
                paths.append(pr)
                
        # map upper impact positions of FP strips to lower impact
        # positions of upper (1,2,3,4,5) WCT strips.
        for pi in range(0,6):   # FP impact positions
            pia = arr[pi]       # shape: (10, nticks)
            assert pia.shape[0] == 10

            # count strips in FP table
            for istrip in range(1,6):
                col = 4 + istrip
                resp = pia[col]
                pitchpos = (istrip - (5-pi)/10.0) * pitch
                pr = PathResponse(resp, pitchpos, wirepos=0)
                paths.append(pr)

        ret[pl] = paths
        print(f'{pl} make {len(paths)} paths')
    return ret


def draw_fp(arrs, pdfname, start=22000, skip=10):
    '''Make multipage pdf file with diagnostic plots from FP-style arrays.

    Input "arrs" holds "raw" numpy arrays as from fpzip2arrs().

    The "start" sets when interesting region of the ends of paths begin.

    The "skip" will decimate paths for plots that otherwise take too
    much time or PDF file space to produce in full resolution.

    Plots include unprocessed views of these arrays as well as result
    of processing to form input to conversion to WCT form.

    '''
    xyz="XYZ"

    with PdfPages(pdfname) as pdf:
        for pl, arr in sorted(arrs.items()):

            nfids, ncols, nsamps = arr.shape
            assert ncols == 10

            # start points
            xyzs = arr[:, 1:4, 0]
            print (pl, arr.shape, xyzs.shape)

            fig, axes = plt.subplots(nrows=3, ncols=1)
            for ind in range(3):
                ax = axes[ind]
                ind2 = (ind+1)%3
                c1 = xyz[ind]
                c2 = xyz[ind2]
                ax.set_title(f'{pl}: start points: {c2} vs {c1}')
                ax.scatter(xyzs[:,ind], xyzs[:,ind2], marker='o')
            plt.tight_layout()
            pdf.savefig(plt.gcf())
            plt.close();

            # paths
            fid_xyzp = arr[:, 1:4, start::skip]

            # reshape to be (nlong, ntran)
            # fidrs = numpy.asarray(range(nfids)).reshape((-1,12))

            # for iset, fids in enumerate(fidrs):
            #     fig = plt.figure()

            #     for ind in range(3):
            #         ax = fig.add_subplot(220+ind+1)
            #         ind2 = (ind+1)%3
            #         ax.set_title(f'{pl}: set {iset} paths: {xyz[ind2]} vs {xyz[ind]}')
            #         ax.set_xlabel(f'{xyz[ind]} [mm]')
            #         ax.set_ylabel(f'{xyz[ind2]} [mm]')
            #         for fid in fids:
            #             xyzp = fid_xyzp[fid]
            #             ax.scatter(xyzp[ind,:], xyzp[ind2,:], s=0.1)

            #     ax = fig.add_subplot(224, projection='3d')
            #     for fid in fids:
            #         xyzp = fid_xyzp[fid]
            #         print(fid, xyzp.shape)
            #         ax.scatter(xyzp[0,:], xyzp[1,:], xyzp[2,:], s=0.1)

            #     plt.tight_layout()
            #     pdf.savefig(plt.gcf())
            #     plt.close();

                
            # Use end but multiple of 20
            nsamps = 20 * ((arr.shape[-1] - start)//20)
            fid_w = arr[:, 4:, -nsamps:]
            fid_w = fid_w.reshape((-1, 12, 6, nsamps))
            # average along strip direction
            fid_w = numpy.mean(fid_w, axis=0)

            # transpose so next flattening makes first dimension the
            # absolute impact position.
            fid_w = numpy.transpose(fid_w, axes=(1,0,2))
            if pl == 'col':
                # shape: (6,12,many)
                lu = list(range(12))
                ld = list(range(12))
                ld.reverse()
                for ind in [1,2,3]:
                    print(f'Swapping collection strip {ind}')
                    fid_w[ind, lu, :] = fid_w[ind, ld, :]

            print("fid_w.shape", fid_w.shape)
            # flatten to absolute impact position
            fid_w = fid_w.reshape((12*6, -1))
            fid_tot = 5*units.nanosecond * numpy.sum(fid_w, axis=1)

            fig = plt.figure()
            ax = fig.add_subplot(111)
            plt.title(f'{pl} raw response summed up strip')
            norm = mpl.colors.TwoSlopeNorm(vmin=numpy.min(fid_w),
                                           vcenter=0.0,
                                           vmax=numpy.max(fid_w))
            plt.imshow(fid_w, aspect='auto',
                       interpolation='none', norm=norm)
            
            ax.set_xlabel(f'tick (5ns bins)')
            ax.set_ylabel('position = pitch + 12*strip')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();

            fig = plt.figure()
            ax = fig.add_subplot(111, aspect='auto')
            plt.title(f'{pl} FP integrated response')
            plt.plot(fid_tot)
            ax.set_xlabel('path index on a strip')
            ax.set_ylabel('integrated current')
            pdf.savefig(plt.gcf())
            plt.close();


            # now we get things into WCT form. 5ns->100ns bins, correct units.
            wct_norm = 1e-3*units.eplus/units.microsecond
            wct_w = wct_norm * numpy.mean(fid_w.reshape(12*6, -1, 20), axis=2)

            fig = plt.figure()
            ax = fig.add_subplot(111)
            plt.title(f'{pl} response, WCT [pA]')
            norm = mpl.colors.TwoSlopeNorm(vmin=numpy.min(wct_w/units.picoampere),
                                           vcenter=0.0,
                                           vmax=numpy.max(wct_w/units.picoampere))
            plt.imshow(wct_w/units.picoampere, aspect='auto',
                       interpolation='none', norm=norm)
            
            ax.set_xlabel(f'tick (100ns bins)')
            ax.set_ylabel('position = pitch + 12*strip')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();

            # integrate each waveform
            wct_tot = 0.1*units.microsecond * numpy.sum(wct_w, axis=1)

            fig = plt.figure()
            ax = fig.add_subplot(111, aspect='auto')
            plt.title(f'{pl} WCT integrated response')
            plt.plot(wct_tot/units.eplus)
            ax.set_xlabel('path index on a strip')
            ax.set_ylabel('integrated current [electron]')
            pdf.savefig(plt.gcf())
            plt.close();
            
            log_w = lg10(wct_w / units.picoampere)
            fig = plt.figure()
            ax = fig.add_subplot(111)
            plt.title(f'{pl} response, WCT scale and sample, "log10"')
            norm = mpl.colors.TwoSlopeNorm(vmin=numpy.min(log_w),
                                           vcenter=0.0,
                                           vmax=numpy.max(log_w))
            plt.imshow(log_w, aspect='auto',
                       interpolation='none', norm=norm)
            
            ax.set_xlabel(f'tick (100ns bins)')
            ax.set_ylabel('position = pitch + 12*strip')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();


