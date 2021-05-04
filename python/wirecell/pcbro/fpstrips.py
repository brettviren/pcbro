#!/usr/bin/env python3
'''
Functions for operating on Francesco Pietropaolo's field response
results.

'''
import os.path as osp
import numpy
from wirecell import units

from matplotlib.backends.backend_pdf import PdfPages
import pylab
import matplotlib.pyplot as plt
import matplotlib as mpl


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


def fpzip2arrs(datgen):
    '''
    Given a data generator yielding (filename, text) from an archive
    of FP's fort.NNN files, such as downloaded from dropbox, return
    corresponding numpy arrays with no processing

    Return dict keyed by ("col", "ind") with values of 3D array with
    layout that spans dimensions of:

    (<fid>, <column>, <sample>)

    Shapes for 2-view are:

        - col: (6x12, 10, many1)

        - ind: (4x12, 10, many2)

    3-view use this function one at a time faking each view as
    "collection".

    The manyN may not be equal.  Each 3D array has <sample> dimension
    zero padded to fit maximum path.
    '''
    all_legal = legal_fids['ind'] + legal_fids['col']

    arrs = list()

    for path, text in datgen:
        fname = osp.basename(path)
        if len(fname) != 8:
            print(f"skipping {fname}")
            continue
        fort,fid = fname.split('.')
        fid = int(fid)
        if fid not in all_legal:
            print(f"skipping {fname}")
            continue

        arr = parse(text)
        arrs.append((fid, arr))

    def reg(alst):
        '''Regularize list of N 2D arrays of shape (many, 10) to 3D array of
        shape (N,10,max(many))
        '''
        nfids = len(alst)
        if nfids == 0:
            print(f'warning: given empty list in fzip2arrs with {len(arrs)}')
            return
        nsamps = max([a.shape[0] for a in alst])
        block = numpy.zeros((nfids, 10, nsamps))
        for i,a in enumerate(alst):
            n = a.shape[0]
            block[i,:,:n] = a.T
        return block
        
    # shape: (12*6 or 12*4, 10, many)

    col=reg([a[1] for a in sorted(arrs) if a[0] > 200]);
    ind=reg([a[1] for a in sorted(arrs) if a[0] < 200]);
    ret = dict()
    if col is not None: ret['col'] = col
    if ind is not None: ret['ind'] = ind
    return ret


def fp2meta(arrs):
    '''
    Return meta data about the responses
    '''
    speed = 0.0
    origin = 0.0

    ret = dict()
    pitches = dict()
    locations = dict()

    for pl, arr in sorted(arrs.items()):
        # nfids, ncols, nsamps = arr.shape

        oo = arr[:,3,1]*fp_dist_unit
        origin += numpy.average(oo)

        # skip first as it was wonky in early calculations
        ss = step_speed(arr[:,:4,1:11])
        speed += numpy.average(ss)

    nt = 1000
    t0 = numpy.average(arr[:,0,1])*units.us
    t1 = numpy.average(arr[:,0,2+nt])*units.us
    period = (t1-t0)/nt

    nplns = len(arrs)
    origin = origin/nplns
    speed = speed/nplns
    print(f'period={period/units.us:10.3f} us, origin={origin/units.mm:10.3f} mm, speed={speed/(units.mm/units.us):10.3f} mm/us')
    ret.update(dict(origin=origin, speed=speed, tstart=0,
                    period = period))
    return ret

        
        
    
def fp2wct(arrs, rebin=20, tshift=0, nticks=None):
    '''
    Convert dict of FP arrays to WCT equivalents

    The "arrs" dict is as returned fpzip2arrs() into WCT equivalent.

    The array values in the dict are of shapes:

    col: (72, 10, many) ind: (48, 10, many)

    The ordering of the 72 or 48 paths are as-provided by FP.  They
    are assumed to be pitch-major ordered.

    Return dict of same keys with each array reduced in size as:

    col: (12, 10, fewer) ind: (12, 10, fewer)

    This will:

        - scale the 10 fort.NNN values to WCT units

        - rebin the samples (many->fewer) periods to match WCT
          convention (5ns to 100ns)

        - average along strip positions for a given impact position
          (6x12 or 4x12 -> 12)

        - regularize impact positions (flip 12 impact positions for
          collection strip>0)

        - force result to be nticks long, padding or truncating the
          *start* of the array.

        - flip induction strips if named "ind1" or "ind2", assuming
          they come from 3view.
    '''
    ret = dict()


    for pl, arr in sorted(arrs.items()):
        nfids, ncols, nsamps = arr.shape
        assert ncols == 10

        # nfids=(nlong*npitch), pitch-major ordering

        # break out the current arrays
        curs = arr[:, 4:, :]           # (nfids, 6, many)
        #print(f'{pl} input curs {curs.shape}')

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
        #print(f'{pl} after mean {curs.shape}')
        
        # FP's field calculation exploits an equivalence symmetry in
        # the strip+hole pattern for collection which is baked into
        # the results.  We undo it by "flipping" the impact positions
        # for collection strips > 0.  If we had to keep distinct the
        # positions along the strip we'd need a second flip in that
        # direction for strip 2 but the reshape+mean negates that
        if pl in ('col','ind1','ind2'):
            lu = list(range(12))
            ld = list(range(12))
            ld.reverse()
            for ind in range(1,6):
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
        curs = numpy.mean(curs.reshape((12, 6, curs.shape[-1]//20 ,-1)), axis=3)
        # shape now (12,6,nsamps/20)

        # FP current is in units of electrons/microsecond and uses
        # 10^3 electrons as the element of drifting charge.  The two
        # domains also pick opposite sign convention.
        norm = -1e-3 * units.eplus/units.microsecond
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
        # print(f'{pl} wc {txyz.shape} coords: {txyz[:,:,0]}')

        # append final zero sample
        shape = list(txyz.shape)
        shape[-1] = -1
        txyz = numpy.concatenate((txyz, txyz[:,:,-1].reshape(shape)), axis=2)
        txyz[:,:,-1] += txyz[:,:,1] - txyz[:,:,0]

        shape = list(curs.shape)
        shape[-1] = 1
        curs = numpy.concatenate((curs, numpy.zeros(shape)), axis=2)

        # rejoin and done
        # print(f'txyz:{txyz.shape}, curs:{curs.shape}')
        # shape: (12, 10, many)
        almost = numpy.concatenate((txyz, curs), axis=1)

        if nticks:
            # if too big clip from start
            if almost.shape[-1] > nticks:
                almost = almost[:,:,-nticks:]
            # if too small, pad to back
            elif almost.shape[-1] < nticks:
                top = list(almost.shape)
                top[-1] = nticks - almost.shape[-1]
                top = numpy.zeros(top)
                almost = numpy.concatenate((top,almost), axis=2)

        # and maybe shift contents preserving nticks
        if tshift:
            s = list(almost.shape)
            s[-1] = abs(tshift)
            extra = numpy.zeros(s)
            if tshift < 0:      # shift forward, lose late
                almost = numpy.concatenate((extra, almost[:,:,:tshift]), axis=2)
            else:               # shift backward, lose early
                almost = numpy.concatenate((almost[:,:,tshift:], extra), axis=2)

        ret[pl] = almost
    return ret

def arrs2pr(wct, pitchdict):
    '''Return dict of PlathResponse lists derived from from "wct" type array as from fp2wct()

    Each array is assumed to be shaped as (12, 10, nsamples).
    '''
    from wirecell.sigproc.response.schema import PathResponse

    ret = dict()
    for pl, arr in wct.items():
        pit = pitchdict[pl]

        #print(f'{pl} input shape {arr.shape}')

        # with PdfPages(f'debug-{pl}.pdf') as pdf:
        #     print(f'{pl} write debug PDF')
        #     junk = arr[:, 4:, :].transpose((1,0,2)).reshape(12*6,-1)
        #     plt.imshow(junk, aspect='auto',
        #                interpolation='none')
        #     plt.colorbar()
        #     pdf.savefig(plt.gcf())
        #     plt.close();

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
                pitchpos = -istrip*pit - (pi-6)*0.1*pit
                #print(f'lo: {pl} {pit} -{istrip} imp={pi-6} pp={pitchpos}')
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
                pitchpos = istrip*pit - (5-pi)*0.1* pit
                #print(f'hi: {pl} {pit} +{istrip} imp={5-pi} pp={pitchpos}')
                pr = PathResponse(resp, pitchpos, wirepos=0)
                paths.append(pr)

        paths.sort(key=lambda pr: pr.pitchpos)

        ret[pl] = paths
        #print(f'{pl} make {len(paths)} paths')
    return ret


fp_time_unit = units.us
fp_dist_unit = units.mm

def step_speed(path_txyz_step):
    '''
    Given (npath,4,nstep) where 4=t,x,y,z return speed.
    '''
    arr = path_txyz_step        # shorthand

    dt = (arr[:,0,1:] - arr[:,0,:-1])*fp_time_unit
    dx = (arr[:,1,1:] - arr[:,1,:-1])*fp_dist_unit
    dy = (arr[:,2,1:] - arr[:,2,:-1])*fp_dist_unit
    dz = (arr[:,3,1:] - arr[:,3,:-1])*fp_dist_unit
    dr = numpy.sqrt(dx*dx + dy*dy + dz*dz)
    
    shape = dr.shape

    dr_l = dr.reshape(-1)
    dt_l = dt.reshape(-1)
    dt_l[dr_l == 0] = 1.0
    v_l = numpy.divide(dr_l, dt_l)
    v = v_l.reshape(shape)
    return v

# t:(0, ..., 119.53)us, 0.005us bins
# x,y shown as path IDs:
# x:(0,1,2,3,4,5,6,7,8,9,10,11, 0,1,2,3,4,5,6,7,8,9,10,11, ...
# y:(0,0,0,0,0,0,0,0,0,0, 0, 0, 1,1,1,1,1,1,1,1,1,1, 1, 1, ...
# z:(199.95, ................., ......................... )mm
# last z value: 16.54 with a ragged end point


def draw_fp_speed(arrs, outfile, start=0.0, **kwds):
    '''
    Draw drift speed as impact vs step
    '''
    sunits = units.mm/units.us
    fp_tick = 5*units.ns
    start_tick = int(start / fp_tick)
    start_us = start/units.us
    print(f'draw speed: start at {start_us} us = {start_tick} FP ticks')
    with PdfPages(outfile) as pdf:

        for pln, arr in sorted(arrs.items()):
            nfids, ncols, nsteps_tot = arr.shape
            print(f'draw speed: {pln}: num FP steps: {nsteps_tot}')
            nsteps = nsteps_tot - start_tick
            assert ncols == 10

            ntran = 12
            nlong = nfids // ntran
            block = arr[:,:4,start_tick:].reshape((nlong, ntran, 4, nsteps))

            extent = [start_us, start_us + nsteps*fp_tick/units.us, 0, ntran]
            fig,axes = plt.subplots(nrows=nlong, sharex=True)
            for ilong in range(nlong):
                speed = step_speed(block[ilong])
                speed = speed[:,1:] # throw away first sample
                if ilong == 0:
                    z = block[ilong,0,3,0]
                    print(f'\torigin: {z/units.mm:.3f} mm, {sunits} us')
                    avgspeed = numpy.average(speed[:10])
                    print(f'\tspeed: {avgspeed/(units.mm/units.us):.3f} mm/us')
                im = axes[ilong].imshow(speed/sunits, aspect='auto', 
                                        extent=extent, interpolation='none')
                axes[ilong].set_ylabel(f'row {ilong}')
            axes[-1].set_xlabel(f'step time [us]')

            axes[0].set_title(f'{pln} drift speeds')
            plt.tight_layout()
            fig.colorbar(im, ax = axes)
            pdf.savefig(plt.gcf())
            plt.close();
            

def draw_fp_waves(arrs, pdfname, start=0, **kwds):
    '''
    Draw representative waveforms
    '''
    fp_tick = 5*units.ns
    start_tick = round(start/fp_tick)


    what = osp.splitext(osp.basename(pdfname))[0]
    with PdfPages(pdfname) as pdf:
        plane_strips = list()
        for pl, arr in sorted(arrs.items()):
            
            nticks = arr.shape[-1]
            t_us = numpy.linspace(start/units.us, fp_tick*nticks/units.us,
                                  nticks-start_tick, endpoint=False)

            strips = numpy.sum(numpy.transpose(arr[:,4:,:], (1,0,2)), axis=1)[:,start_tick:]

            for ind, s in enumerate(strips):
                plt.plot(t_us, s/72, label=f'strip {ind}')
            
            plt.title(f"{pl} integrated per strip ({what})")
            plt.ylabel("integrated current")
            plt.xlabel("time [us]")
            plt.legend()
            pdf.savefig(plt.gcf())
            plt.close();


def draw_fp_sum(arrs, pdfname, **kwds):
    '''
    Integrate over time
    '''
    what = osp.splitext(osp.basename(pdfname))[0]
    with PdfPages(pdfname) as pdf:
        plane_strips = list()
        for pl, arr in sorted(arrs.items()):

            tots_eps = 0.1
            tots = numpy.sum(arr[:,4:,:], axis=-1).T
            tots[tots<tots_eps] = tots_eps  # 1e6 is peak collection
            plt.imshow(numpy.log10(tots), aspect='auto')
            plt.colorbar()        
            plt.title(f"{pl} integrated FR, log10")
            plt.ylabel("strip")
            plt.xlabel("impact")
            pdf.savefig(plt.gcf())
            plt.close();


            tots = numpy.sum(arr[:,4:,:], axis=-1)
            tots_flat = numpy.flip(numpy.transpose(tots.reshape(-1,12,6), (2,1,0)), axis=1).reshape(-1)
            plt.title(f"{pl} plane ({what})")
            plt.ylabel("integrated current")
            plt.xlabel("impact postion")
            plt.plot(tots_flat)
            pdf.savefig(plt.gcf())
            plt.close();
            
            tots_strip = numpy.sum(numpy.transpose(arr[:,4:,:], (1,0,2)).reshape(6,-1), axis=-1)
            plane_strips.append((pl, tots_strip))

        for name, tots in plane_strips:
            #print (f'STRIP {name} {tots}')
            plt.step(range(len(tots)), numpy.abs(tots), label=name, where='post')
        plt.yscale('log')
        plt.legend()
        plt.title("Strip totals (abs)")
        plt.ylabel("integrated current")
        plt.xlabel("strip number")
        pdf.savefig(plt.gcf())
        plt.close();



def draw_fp_diag(arrs, pdfname, start=0*units.us, skip=10, **kwds):
    '''
    Make multipage pdf file with diagnostic plots from FP-style
    arrays.

    Input "arrs" holds "raw" numpy arrays as from fpzip2arrs().

    The "start" sets when interesting region of the ends of paths
    begin.

    The "skip" will decimate paths for plots that otherwise take too
    much time or PDF file space to produce in full resolution.

    Plots include unprocessed views of these arrays as well as result
    of processing to form input to conversion to WCT form.
    '''
    xyz="XYZ"

    fp_tick = 5*units.ns
    start = round(start/fp_tick)

    # bit of evil, likely to break
    what = osp.splitext(osp.basename(pdfname))[0]

    with PdfPages(pdfname) as pdf:
        for pl, arr in sorted(arrs.items()):

            nfids, ncols, nsamps = arr.shape
            assert ncols == 10

            # start points
            xyzs = arr[:, 1:4, 0]
            #print (pl, arr.shape, xyzs.shape)

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
            # fid_xyzp = arr[:, 1:4, start::skip]

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

            #print("fid_w.shape", fid_w.shape)
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
            plt.title(f'{pl} response, WCT scale and sample, "log10+5"')
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


