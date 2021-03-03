#!/usr/bin/env python3
'''
Provide simple event display for 50L.
'''
import os
import time
import numpy
import matplotlib.pyplot as plt 
import matplotlib as mpl
Normer = mpl.colors.TwoSlopeNorm

class Dataset50L:
    '''
    Wrap a raw or signal dataset for 50L.
    '''
    def __init__(self, dat, tier="raw", name='', run=''):
        '''Create a data set on a set of arrays.

        The dat is a dict as saved by wire-cell + pcbro raw data
        decoding and signal processing jobs.  It has keys like:

            <type>_<tag>_<trignum>

        With:
        - type as frame, channels, tickinfo
        - tag is WCT frame tag, may be empty (eg as in raw)
        - trignum is the trigger number

        The "tier" labels the data tier, raw or sig.

        The "name" may provide some human-oriented qualifying identity.

        The "run" may provide some human-oriented run identifier
        '''
        self.dat = dat
        self.tier = tier
        self.name = name
        self.run = run
        
    @property
    def trigs(self):
        tt = [k.split("_")[-1] for k in self.dat if k.startswith("frame_")]
        tt = [int(t) for t in set(tt)]
        tt.sort()
        return tt

    @property
    def nplanes(self):
        return len(self.channels)

    @property
    def channels(self):
        '''Return range of channel INDICES (not IDs) for each plane. 

        Note, this ordering is reversed from WCT convention and
        assumes things about the producer of the dataset!
        '''
        cc = [(0,64), (64,128), (128,192)]
        return cc

def secs_from_centiseconds(cs):
    if isinstance(cs,str):
        return int(cs[:-2])
    assert(isinstance(cs, int))
    return cs // 100

def cern_time_from_secs(secs):
    oldtz = os.environ.get("TZ", None)
    os.environ["TZ"] = "CET"
    time.tzset()
    ts = time.asctime(time.localtime(secs))
    if oldtz is None:
        os.environ.pop("TZ")
    else:
        os.environ["TZ"] = oldtz
    time.tzset()
    return ts

def ts_from_bin(binname):
    'Return a run timestamp by parsing raw .bin file name/path'
    parts = os.path.splitext(os.path.basename(binname))[0].split("_")
    secs = secs_from_centiseconds(parts[-1])
    return cern_time_from_secs(secs)

def ds_from_50l_npz(npzname, name='', run=''):
    'Return Dataset from a 50-L NPZ file assuming conventions'
    arrs = numpy.load(npzname)
    if npzname.startswith("sig"):
        tier="sig"
    if npzname.startswith("raw"):
        tier="raw"
    return Dataset50L(arrs, tier=tier, name=name, run=run)

class Main:
    '''
    Main display class
    '''

    default_opts = dict(
        baseline_subtract='', # or 'median'
        tag='',               # frame tag, eg 'gauss0' for sig
        aspect='auto',        # 
        color_range=None,     # or (min,max), or (min,center,max)
        color_unit='',        # set name for color scale
        color_map=None,       # color map name, default depends on dataset.tier
        # labels for planes, indexed as (col, ind[, fake ind])
        cnames=["collection","induction"],
        channels=None,      # set to limit channels to display, as string '0:50,64:110' or list of list
        planes=None,        # set to limit which planes to display, as string '1,2'
        tshift=0,           # shift data this many ticks
        ticks=(0,650),      # range of ticks to display
        mask_min=None,      # if set, mask out small values 
        # set an overall title, possibly templated on some available values
        title='{name} {tier} run:{run} trigger:{trignum}/{ntrigs} ({tag})',
    )

    def __init__(self, dataset=None, fig=None, **opts):
        '''
        Create display on a dataset.  

        The opts dictionary controls display options.
        '''
        self.ds = dataset
        self.trignum = self.ds.trigs[0]
        self._opts = dict(self.default_opts)
        self._opts.update(opts)
        self._fa = None
        self._cb = None
        self._fig = fig or plt.figure(tight_layout=True)
        self._fig.set_tight_layout(True)
        self._axes = None

    def __getattr__(self, key):
        return self._opts[key]

    def set_option(self, key, value):
        if key in self._opts:
            self._opts[key] = value
            return
        raise KeyError(f'no such option: "{key}"')

    @property
    def frame_key(self):
        'Key name for current frame'
        return f'frame_{self.tag}_{self.trignum}'

    @property
    def frame(self):
        'Current frame'
        key = self.frame_key
        farr = numpy.array(self.ds.dat[key])
        if self.baseline_subtract == 'median':
            farr = farr - numpy.median(farr, axis=0)
        #print(f'frame: {key}')
        return farr

    @property
    def ticks(self):
        tt = self._opts['ticks']
        if isinstance(tt, str):
            tt = list(map(int, tt.split(":")))
        return tt

    @property
    def channels(self):
        cc = self._opts['channels']
        if not cc:
            return self.ds.channels
        if isinstance(c, str):
            cc = [list(map(int, ss.strip().split(":"))) for ss in c.split(",")]
        return cc

    @property
    def planes(self):
        'Return list of plane indices to display (col=0, ind=1, NOT WCT)'
        p = self._opts['planes']
        if not p:
            return (0,1)        # not WCT plane IDs!
        if isinstance(p, str):
            p = p.replace("col","0").replace("ind","1")
            return list(map(int, p.split(",")))
        return p

    @property
    def color_range(self):
        cr = self._opts['color_range']
        if isinstance(cr, str):
            cr = list(map(float, cr.split(',')))
        if cr is None:
            cr = [numpy.min(self.frame), numpy.max(self.frame)]
        if len(cr) == 2:
            cr.insert(1, 0.5*numpy.sum(cr))
        if cr[0] >= cr[1]:
            cr[0] = cr[1]-1.0
        if cr[2] <= cr[1]:
            cr[2] = cr[1]+1.0
        return cr
            
    @property
    def color_unit(self):
        cu = self._opts['color_unit']
        if cu:
            return cu
        return dict(raw='ADC', sig='ionization electrons').get(self.ds.tier, '')

    @property
    def title(self):
        return self.sformat(self._opts['title'])

    @property
    def as_dict(self):
        return dict(tier=self.ds.tier,
                        name=self.ds.name,
                        run=self.ds.run,
                        tag=self.tag,
                        trignum=self.trignum,
                        ntrigs=len(self.ds.trigs))

    def sformat(self, template):
        return template.format(**self.as_dict)

    @property
    def tshift(self):
        return int(self._opts['tshift'])

    def fwd(self, trignum=None):
        tn = self.trignum
        trigs = self.ds.trigs
        if tn == trigs[-1]:
            print(f'already at last trig #{tn} of {len(trigs)} total')
            return
        if trignum is None:
            ind = trigs.index(tn)
            self.trignum = trigs[ind+1]
        else:           
            tn = int(trignum)
            ind = trigs.index(tn)
            self.trignum = trigs[ind]
        self.draw()


    def draw(self):
        '''
        Craw current event
        '''
        tt = self.ticks
        channels = self.channels
        nplanes = len(self.planes)
        cr = self.color_range
        norm = Normer(vmin=cr[0], vcenter=cr[1], vmax=cr[2])

        frame = self.frame
        if self._axes is None:
            self._axes = self._fig.subplots(1, nplanes, sharey=True)

        for axind, pind in enumerate(self.planes):
            ax = self._axes[axind]
            ax.clear()

            cc = channels[pind]
            
            src_t0 = tt[0]-self.tshift
            src_dt = tt[1]-tt[0]
            tgt_t0 = 0
            tgt_dt = src_dt

            bshrink = -src_t0
            if bshrink > 0:
                tgt_t0 += bshrink
                tgt_dt -= bstrink
                src_dt -= bshrink
                src_t0 = 0
            tshrink = src_t0 + src_dt - frame.shape[0]
            if tshrink > 0:
                src_dt -= tshrink
                tgt_dt -= tshrink

            #print(f'{src_t0}+{src_dt} {tgt_t0}+{tgt_dt}')
            sa = numpy.zeros((tt[1]-tt[0], cc[1]-cc[0]))
            sa[tgt_t0:tgt_t0+tgt_dt,:] += numpy.array(frame[src_t0:src_t0+src_dt, cc[0]:cc[1]])

            if self.mask_min is not None:
                sa = numpy.ma.masked_where(sa < self.mask_min, sa)

            im = ax.imshow(sa, interpolation='none',
                           norm=norm,
                           cmap=self.color_map,
                           aspect=self.aspect,
                           extent=[cc[0],cc[1],tt[1],tt[0]])
            ax.set_xlabel(f'{self.cnames[pind]} channels')
            ax.invert_yaxis()
            # ax.set_xticks
        self._axes[0].set_ylabel('sample period [count]')

        if self._cb is None:
            self._cb = self._fig.colorbar(im)
            self._cb.set_label(self.color_unit)
        self._cb.update_normal(im)

        self._fig.subplots_adjust(top=0.90)
        self._fig.suptitle(self.title, fontsize=14)
        self._fig.tight_layout()
        #plt.show()


    def save(self, fname):
        'Save current display to a file'
        plt.savefig(fname, bbox_inches='tight')

class MainN:
    def __init__(self, mains, **kwds):
        self.mains = mains
        for k,v in kwds.items():
            self.set_option(k,v)

    def draw(self):
        for m in self.mains:
            m.draw()
    def fwd(self, trignum=None):
        for m in self.mains:
            m.fwd(trignum)
    def set_option(self, key, val):
        for m in self.mains:
            m.set_option(key, val)
    def save(self, fpattern):
        for m in self.mains:
            m.save(m.sformat(fpattern))

def plot_figures(figures, nrows = 1, ncols=1):
    """Plot a dictionary of figures.

    Parameters
    ----------
    figures : <title, figure> dictionary
    ncols : number of columns of subplots wanted in the display
    nrows : number of rows of subplots wanted in the figure
    """

    fig, axeslist = plt.subplots(ncols=ncols, nrows=nrows)
    for ind,title in enumerate(figures):
        axeslist.ravel()[ind].imshow(figures[title], cmap=plt.gray())
        axeslist.ravel()[ind].set_title(title)
        axeslist.ravel()[ind].set_axis_off()
    plt.tight_layout() # optional

def test():

    run='Tue May 26 11:07:38 2020'
    raw = ds_from_50l_npz("raw.npz", name="Decoded", run=run)
    sig = ds_from_50l_npz("sig.npz", name="Signal", run=run)

    rm = Main(raw, baseline_subtract="median")
    sm = Main(sig, tag='gauss0', mask_min=0.0)
    disp = MainN([rm, sm], ticks='250:650')


    disp.fwd(21)
    disp.fwd()
    
    return disp

