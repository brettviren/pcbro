#!/usr/bin/env python3
'''
Deal with garfield files

File names:

  <S.S>_[col|ind]_[L|R]_[a|b].dat

S.S is electron shift in {0.0, 0.5, ..., 2.5} cm.
col|ind is collection or induction 

'''
import os.path as osp
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict
import numpy

#fixme: this cross-package import indicates we should refactor.
import wirecell.sigproc.garfield as wctgf

def parse_filename(filename):
    '''Try to parse whatever data is encoded into the file name.

    eg: "pcb_try/0.5_ind_L_a.dat" returns dictionary:

        {'ab': 'a', 'LR': 'L', 'plane': 'ind', 'dist': '0.5',
         'filename': '0.5_ind_L_a.dat'}
    '''
    filename = osp.split(filename)[-1]
    dist, plane, LR, ab = osp.splitext(filename)[0].split('_')
    return locals()

def tar_source(tarfilename):
    return wctgf.asgenerator(tarfilename)

def dir_source(dirname, planes=None):
    import glob
    for fname in glob.glob(osp.join(dirname, '*.dat')):
        if planes:
            pf = parse_filename(fname)
            if not pf['plane'] in planes:
                continue
        yield (fname, open(fname, 'rb').read().decode())

def load(source):
    '''
    Load data from a sequence of (filename, contents) pairs
    '''
    source = tar_source(source)
    for fn,text in source:
        fninfo = parse_filename(fn);
        print (fninfo)
        gen = wctgf.split_text_records(text)

        for rec in gen:

            dat = wctgf.parse_text_record(rec)
            keys = list(dat.keys())
            for die in "signal created x y xlabel ylabel".split():
                keys.remove(die)
            s = " ".join(["%s:{%s}"%(k,k) for k in keys])
            print (s.format(**dat))

        
def dat2npz(datfilename, npzfile):
    fninfo = parse_filename(datfilename)
    gen = wctgf.split_text_records(open(datfilename,'rb').read().decode())

    ret = defaultdict(list)
    for rec in gen:
        dat = wctgf.parse_text_record(rec)
        for k,v in dat.items():
            ret[k].append(v)
    arrs=dict()
    for k,v in ret.items():
        arrs[k] = numpy.asarray(v)
    numpy.savez(npzfile, **arrs)


# At one radial impact position we have a family of responses each
# defined on a "micro-wire" which makes up one segment of an overall
# strip conductor.  This object holds the transverse position (pos)
# and the response array (resp) for one such "micro-wire".
@dataclass
class Ripresp:
    ypos: float
    resp: numpy.ndarray

# A radial impact position is at a discrete radius ("rad") near the
# hole about which the Garfield responses are calculated.  The "resps"
# item is a list of Ripresp objects sorted by their pos.
@dataclass
class Rip:
    rad: float
    resps: List[Ripresp]

# The plane is named 'ind' or 'col' and the 'pos' indicates location
# in the drift direction, 'voltage' gives bias voltage.  The 'rips'
# holds a dictionary of Rip objects keyed by the radius as a string
# (eg, '0.0')
@dataclass
class Riplane:
    name: str
    xpos: float
    voltage: float
    rips: Dict[str, Rip]

class Ripem(object):
    '''
    Radial Impact Position Extreme Manipulation!
    '''
    
    def __init__(self, source=None):
        self.ticks = None       # will hold an array of common response sample times
        self.plane = dict()     # key by 'ind' or 'col' gives Riplane
        if source:
            self.load(source)

    def responses(self, plane, radius, span):
        '''Return a collection of responses as 2D array.  

        Each row is a one response on a micro-wire.

        The plane is the name ('ind' or 'col').  Radius is given as a
        float or more exactly as string (eg '0.5').  Span is given as
        a pair of floating point numbers which are compared against
        micro-wire center positions.
        '''
        riplane = self.plane[plane]
        if isinstance(radius, float):
            radius = "%0.1f" % radius
        rip = riplane.rips[radius]
        assert(len(rip.resps)>0)
        res = list()
        for rr in rip.resps:
            if rr.ypos >= span[0] and rr.ypos <= span[1]:
                res.append(rr.resp)
        return numpy.asarray(res)
            
    def load(self, source):
        '''
        Load a source of data.  Source must be sequence of (filename,text)
        '''
        for filename, text in source:
            self.load_file(filename, text)
    def load_file(self, filename, text=None):
        '''Load one garfield file.  If text is not given, read file.

        Result is stored in an index based on the plane ('ind' or
        'col') and the radial impact position ("rip") which measured
        relative to the hole center.  
        '''
        if text is None:
            text = open(filename,'rb').read().decode()
        fninfo = parse_filename(filename);

        # file level indicies
        plane = fninfo['plane'] # 'col', 'ind'
        rad = fninfo['dist'] # impact radius as string

        gen = wctgf.split_text_records(text)
        del(text)

        # Some plane-common values are repeated, we assert they are common.
        dats = [wctgf.parse_text_record(rec) for rec in gen]

        try:
            riplane = self.plane[plane]
        except KeyError:        # first time to see this plane
            dat0 = dats[0]
            xpos = dat0['wire_region_pos'][1] # X-position (drift, common)
            voltage = dat0['bias_voltage']
            self.plane[plane] = Riplane(plane, xpos, voltage, dict())
            riplane = self.plane[plane]

        try:
            rip = riplane.rips[rad]
        except KeyError:        # first time to see this radius
            riplane.rips[rad] = Rip(float(rad), list())
            rip = riplane.rips[rad]

        resps = dict()          # collect by group
        for dat in dats:
            group = dat['group']

            ticks = numpy.asarray(dat['x'])
            if self.ticks is None:
                self.ticks = ticks
            else:
                assert(numpy.all(ticks == self.ticks)) # assure identical sample times
            resp = numpy.asarray(dat['y'])
            wrp = dat['wire_region_pos'];
            assert(wrp[1] == riplane.xpos) # common x for all in a plane
            assert(dat['bias_voltage'] == riplane.voltage) # common voltage for all in a plane

            try:
                rr = resps[group]
            except KeyError:
                resps[group] = Ripresp(wrp[0], resp)
            else:
                assert(rr.ypos == wrp[0]) # common y for all in a group
                rr.resp += resp
        rip.resps.extend(resps.values())
        rip.resps.sort(key=lambda x: x.ypos)
        nresps = len(rip.resps)
        print(f'loaded r={rad} pln={plane} have {nresps} responses')
### keys in object returned from parse_text_records():
# ['created', 'signal', 'group', 'wire_region', 'label',
#  'wire_region_pos', 'bias_voltage', 'nbins', 'xlabel', 'ylabel',
#  'x', 'y']


# Each strip impact response is calcualted from a number of RIPs and
# on each RIP we select a range of "micro wire" responses.
@dataclass
class Siprip:
    'A radius impact and ranges'
    rip: float                  # the impact radius
    cen: float                  # center of hole along slice, relative to strip centerline
    sign: float                 # +1 if rip is "up", -1 if we "flip" the hole
    ranges: List                # list of pairs of float

@dataclass
class Sip:
    'A strip impact position and its rip and ranges'
    impact: float               # impact position
    srs: List[Siprip]          # contributing Siprips

@dataclass
class Strip:
    'A strip worth of responses'
    number: int                 # Strip over which a path drifts (in {-5,5})
    dslice: float
    sips: List[Sip]             # ordered list of strip impact positions.

def sip_ind_strip0():
    slice_1 = [(1.0, 2.5), (-2.5, -1.0)]
    slice_2 = [(1.0, 4.0)]      # flipped
    ips = [0.5*i for i in range(6)]
    return Strip(0, 2.5, 
                 [Sip(ip, [Siprip(    ip, 0.0, +1, slice_1),
                           Siprip(2.5-ip, 2.5, -1, slice_2)]) for ip in ips])
        
def sip_ind_stripp(n):
    assert n>0
    d = (n-1)*5.0
    slice_1 = [(-4.0-d, -2.5-d), (-7.5-d, -6.0-d)]
    slice_2 = [(6.0+d, 9.0+d)]  # flipped
    ips = [0.5*i for i in range(6)]    
    return Strip(n, 2.5,
                 [Sip(ip, [Siprip(    ip, 0.0, +1, slice_1),
                           Siprip(2.5-ip, 2.5, -1, slice_2)]) for ip in ips])

def sip_ind_stripm(n):
    assert n>0
    d = (n-1)*5.0
    slice_1 = [(2.5+d,4.0+d),(6.0+d, 7.5+d)]
    slice_2 = [(-4.0-d, -1.0-d)] # flipped
    ips = [0.5*i for i in range(6)]    
    return Strip(-n, 2.5,
                 [Sip(ip, [Siprip(    ip, 0.0, +1, slice_1),
                           Siprip(2.5-ip, 2.5, -1, slice_2)]) for ip in ips])
    
def sip_ind(sn):
    if sn > 0: 
        return sip_ind_stripp(sn)
    if sn < 0:
        return sip_ind_stripm(-sn)
    return sip_ind_strip0()

def draw_strip(strip):
    import matplotlib.pyplot as plt
    snum = strip.number
    scenter = snum*5
    strip_x = abs(snum)*8
    if snum < 0:
        strip_x -= 4
    
    ax = plt.gcf().gca()
    plt.plot([strip_x,strip_x], [scenter-2.5, scenter+2.5])

    for isip, sip in enumerate(strip.sips):
        strip_impact = sip.impact
        siy = scenter + strip_impact

        # draw strip impact position lines
        plt.plot([strip_x,strip_x+2*strip.dslice], [siy, siy])

        for islice, sr in enumerate(sip.srs):
            slc_x = (1+islice)*strip.dslice + strip_x
            cir_y = sr.cen + scenter
            cir_x = slc_x

            if isip == 0:       # don't redraw a bunch of times
                #print (f"{isip} {islice} circle: {cir_x} {cir_y}")
                circle = plt.Circle((cir_x, cir_y), 1)
                ax.add_artist(circle)

            # slice line
            #plt.plot([slc_x,slc_x], [scenter-2.5, scenter+2.5])

            mar_y = cir_y + sr.rip
            mar_x = slc_x + isip*.2
            # the signed radius point
            marker = "2"        # up
            if sr.sign < 0: marker="1" # down
            plt.plot(mar_x, mar_y, marker)

            for ir, r in enumerate(sr.ranges):
                # draw a range from the marker
                y0 = cir_y + sr.sign * r[0]
                y1 = cir_y + sr.sign * r[1]
                plt.plot([mar_x, mar_x],
                         [y0, y1])
def draw_ind(strips):
    import matplotlib.pyplot as plt
    import pylab
    plt.clf()
    pylab.subplot(aspect='equal') 
    for sn in strips:
        draw_strip(sip_ind(sn))


class Sipem(object):
    '''
    Strip Impact Position Extreme Manipulation! 
    '''
    
    def __init__(self, ripem):
        self.ripem = ripem

    def response(self, plane, strip, sip, slices=[0,1]):
        '''
        Return the response.
        '''
        sipmeth = eval("sip_" + plane) # evil, I know
        strip = sipmeth(strip)
        sips = [s for s in strip.sips if s.impact == sip]
        assert(len(sips) == 1)
        srs = sips[0].srs
        res = list()
        for islice in slices:
            sr = srs[islice]
            for span in sr.ranges:
                r = self.ripem.responses(plane, sr.rip, span)
                if len(r.shape) != 2:
                    print(f'No response for plane:{plane} rad:{sr.rip} span:{span}')
                    continue
                assert(r.shape[0])
                r = r.sum(axis=0)
                res.append(r)
        res = numpy.asarray(res)
        res = res.sum(axis=0)
        res /= len(slices)
        return res
    
    def asarray(self, plane, slices=[0,1]):
        nticks = len(self.ripem.ticks)
        
        # duplicate 6 sips per strip
        ret = numpy.zeros((11 * 12, nticks))
        for istrip in range(-5,6):
            p_row0 = (5 + istrip)*12
            m_row0 = (5 - istrip)*12
            for isip in range(6):
                sip = isip*0.5
                res = self.response(plane, istrip, sip, slices)

                p_row = p_row0 + 6 + isip

                ret[p_row,:] = res

        ret += numpy.flip(ret, axis=0)
        return ret

def plots(source, pdf_file="pcbro.pdf"):
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    #ripem = Ripem(pcbgf.tar_source(tar_file))
    ripem = Ripem(source)
    sipem = Sipem(ripem)


    with PdfPages(pdf_file) as pdf:

        for strips in [[0], [-1,0,1], list(range(-5,6))]:
            draw_ind(strips)
            pdf.savefig(plt.gcf())
            plt.close();

        for strips in [[0],[1],[0,1]]:
            a = sipem.asarray('ind', strips)
            plt.clf()
            plt.imshow(a, aspect='auto')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();

            plt.clf()
            plt.imshow(a[40:90, 600:800], aspect='auto')
            plt.colorbar()
            pdf.savefig(plt.gcf())
            plt.close();
            
