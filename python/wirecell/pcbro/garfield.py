#!/usr/bin/env python3
'''
Deal with garfield files

File names:

  <S.S>_[col|ind]_[L|R]_[a|b].dat

S.S is electron shift in {0.0, 0.5, ..., 2.5} cm.
col|ind is collection or induction 

'''
import os.path as osp
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import List, Dict
import numpy
from wirecell import units
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
        try:
            rip = riplane.rips[radius]
        except KeyError:
            keys = list(riplane.rips.keys())
            print(f'radius:{radius} plane:{plane}, keys:{keys}')
            raise
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


def sign(x): return -1 if x < 0 else +1

def _xxx_strips(ranges, slice_size, strips_data):
    strips = list()
    for istrip, snum in enumerate(range(-5,6)):
        strip_data = strips_data[istrip]
        slc0 = strip_data.slices[0]
        slc1 = strip_data.slices[1]
        sips = list()
        for isip in range(6):
            isip0 = slc0.sips[isip]
            isip1 = slc1.sips[isip]

            # sign of the radial impact position (above/below center)
            s0 = 1
            r0 = isip0.rip
            if r0 < 0:
                s0 = -1
                r0 *= -1

            s1 = 1
            r1 = isip1.rip
            if r1 < 0:
                s1 = -1
                r1 *= -1

            # signed distance from strip0 center to hole center
            d0 = snum*5.0 + isip0.cen
            d1 = snum*5.0 + isip1.cen

            # the strip0 integration ranges translated to stripN
            ranges0 = ranges[0] - d0
            ranges1 = ranges[1] - d1

            # We only have data for "postive" radius so invert if rip
            # is negative.
            if s0 < 0:
                ranges0 *= -1
                ranges0 = numpy.flip(ranges0, axis=1)
            if s1 < 0:
                ranges1 *= -1
                ranges1 = numpy.flip(ranges1, axis=1)

            s = Sip(isip*0.5,
                    [Siprip(r0, isip0.cen, s0, ranges0),
                     Siprip(r1, isip1.cen, s1, ranges1)])
            sips.append(s)
        strips.append(Strip(snum, slice_size, sips))
    return strips

def fix_ranges(rr):
    ret = list()
    for r in rr:
        if r[0] < r[1]:
            ret.append(r)
        else:
            ret.append((r[1],r[0]))
    return numpy.asarray(ret)

def xxx_strips(strips_data, slice_size):
    strips = list()
    for istrip, snum in enumerate(range(-5,6)):
        strip_data = strips_data[istrip]
        slc0 = strip_data.slices[0]
        slc1 = strip_data.slices[1]
        sips = list()
        for isip in range(6):
            isip0 = slc0.sips[isip]
            isip1 = slc1.sips[isip]

            ranges0 = fix_ranges(isip0.wir(snum))
            ranges1 = fix_ranges(isip1.wir(snum))

            s = Sip(isip*0.5,
                    [Siprip(isip0.rip, isip0.cen, isip0.dir, ranges0),
                     Siprip(isip1.rip, isip1.cen, isip1.dir, ranges1)])
            sips.append(s)
        strips.append(Strip(snum, slice_size, sips))
    return strips
    

sip_col_slice = 2.5
sip_ind_slice = 3.3/2.0

def col_strips():
    from . import holes
    strips = holes.get_strips("col")
    return xxx_strips(strips, sip_col_slice)
def ind_strips():
    from . import holes
    strips = holes.get_strips("ind")
    return xxx_strips(strips, sip_ind_slice)
    


# def _col_strips():
#     from . import holes
#     plane_data = holes.planes["col"]
#     ranges = [                  # per slice, strip 0
#         numpy.asarray([(-2.5, -1.8), (0.2, 1.5)]),
#         numpy.asarray([(-1.5, -0.2), (1.8, 2.5)]),
#     ]
#     return xxx_strips(ranges, sip_col_slice,
#                       [plane_data.strips[snum%2] for snum in range(-5,6)])

# def _ind_strips():
#     from . import holes
#     plane_data = holes.planes["ind"]
#     ranges = [                  # per slice, strip 0
#         numpy.asarray([(-2.5, -1.0), (1.0, 2.5)]),
#         numpy.asarray([(-1.5, -0.0), (0.0, 1.5)]),
#     ]
#     return xxx_strips(ranges, sip_ind_slice,
#                       [plane_data.strips[0] for snum in range(-5,6)])

    

def draw_strip(strip):
    import matplotlib.pyplot as plt
    import pylab
    pylab.subplot(aspect='equal');

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

            #if isip == 0:       # don't redraw a bunch of times
            #print (f"{isip} {islice} circle: {cir_x} {cir_y}")
            circle = plt.Circle((cir_x, cir_y), 1)
            ax.add_artist(circle)

            # slice line
            #plt.plot([slc_x,slc_x], [scenter-2.5, scenter+2.5])

            mar_y = cir_y + sr.sign*sr.rip
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

class Sipem(object):

    '''
    Strip Impact Position Extreme Manipulation! 
    '''
    
    def __init__(self, ripem):
        self.ripem = ripem

        self.strips = dict(
            col = {s.number:s for s in col_strips()},
            ind = {s.number:s for s in ind_strips()})

    def wire_region_pos(self, plane, snum):
        'Return position of strip'
        pl = self.ripem.plane[plane]
        x = pl.xpos             # longitiduinal drift direction
        y = snum * 5.0*units.cm # transverse direction
        return (x,y)

    @property
    def ticks(self):
        'Sample time of response function'
        return self.ripem.ticks


    def response(self, plane, strip, sip, slices=[0,1]):
        '''
        Return response function for plane/strip and impact on one slice or average over slices.
        '''
        #print (f'Sipem.response: plane:{plane}, strip:{strip}, sip:{sip}')
        strip = self.strips[plane][strip]
        sips = [s for s in strip.sips if s.impact == sip]
        #print (f'response sips: {sips}')
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
        'Return plane response as numpy array'
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

    def asrflist(self, strategy=None):
        '''
        Return ResponseFunctions.

        The available strategy:
        - None :: u = v
        - "slice" :: u=slice1, v=slice2

        Support when we have it:
        - "hole" :: u=small hole, v=large hole

        '''
        from wirecell.sigproc.response import ResponseFunction as RF

        supported_planes = ["ind","col"]

        times = self.ticks
        t0 = int(times[0])
        tf = int(times[-1])
        ls = (t0, tf, len(times))

        ret = list()
        for istrip in range(-5,6):
            p_row0 = (5 + istrip)*12
            m_row0 = (5 - istrip)*12
            for isip in range(6):
                sip = isip*0.5

                # strategies only affect induction
                pos = self.wire_region_pos("col", istrip)
                res = self.response("col", istrip, sip, [0,1])
                rf = RF("w", istrip, pos, ls, res, sip)
                ret.append(rf)

                if strategy is None:
                    pos = self.wire_region_pos("ind", istrip)
                    res = self.response("ind", istrip, sip, [0,1])
                    rf = RF("u", istrip, pos, ls, res, sip)
                    ret.append(rf)
                    rf = RF("v", istrip, pos, ls, res, sip)
                    ret.append(rf)
                    continue
                
                if strategy == "slice":
                    pos = self.wire_region_pos("ind", istrip)
                    res = self.response("ind", istrip, sip, [0])
                    rf = RF("u", istrip, pos, ls, res, sip)
                    ret.append(rf)
                    res = self.response("ind", istrip, sip, [1])
                    rf = RF("v", istrip, pos, ls, res, sip)
                    ret.append(rf)
                    continue

                raise ValueError(f"unsupported strategy: {strategy}")
        return ret

def plots_geom(pdf_file="pcbro.pdf"):
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    with PdfPages(pdf_file) as pdf:

        for one in ind_strips():
            draw_strip(one)
        plt.title(f'ind strips')
        pdf.savefig(plt.gcf())
        plt.close();

        for one in ind_strips():
            draw_strip(one)
            plt.title(f'ind strip {one.number}')
            pdf.savefig(plt.gcf())
            plt.close();

        for one in col_strips():
            draw_strip(one)
        plt.title(f'col strips')
        pdf.savefig(plt.gcf())
        plt.close();

        for one in col_strips():
            draw_strip(one)
            plt.title(f'col strip {one.number}')
            pdf.savefig(plt.gcf())
            plt.close();

def plots(source, pdf_file="pcbro.pdf"):
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    #ripem = Ripem(pcbgf.tar_source(tar_file))
    ripem = Ripem(source)
    sipem = Sipem(ripem)


    with PdfPages(pdf_file) as pdf:

        for iszoom in [False, True]:
            for plane in ['ind','col']:
                for slices in [[0],[1],[0,1]]:
                    print(f'plotting {plane}')
                    a = sipem.asarray(plane, slices)
                    tit = f'{plane} plane, slice:{slices}'
                    if iszoom: tit += ', zoomed'
                    plt.clf()
                    implo=ticlo = 0
                    imphi,tichi = a.shape
                    slo = imphi // 2 - 6 - 0.5
                    shi = imphi // 2 + 6 - 0.5
                    plt.imshow(a, aspect='auto')
                    if iszoom:
                        plt.xlim(700,800)
                        plt.ylim(imphi//2 - 30, imphi//2 + 30)
                    plt.colorbar()
                    plt.title(tit)
                    plt.ylabel('impacts (0.5 mm spacing)')
                    plt.xlabel('ticks (0.1 us)')
                    plt.plot([ticlo,tichi],[slo,slo], linewidth=0.1, color='red')
                    plt.plot([ticlo,tichi],[shi,shi], linewidth=0.1, color='red')
                    pdf.savefig(plt.gcf())
                    plt.close();

            
def convert(source, outputfile = "wire-cell-garfield-fine-response.json.bz2",
            average=False, shaped=False):
    '''Convert a source (dir or tar) of Garfield file pack into an output
    wire cell field response file.

    See also wirecell.sigproc.response.persist
    See also wirecell.sigproc.ResponseFunction
    '''

    ripem = Ripem(source)
    sipem = Sipem(ripem)
    

    rflist = sipem.asrflist(strategy="slice")
    if shaped:
        rflist = [d.shaped() for d in rflist]
    if average:
        rflist = wctrs.average(rflist)
    wctrs.write(rflist, outputfile)

