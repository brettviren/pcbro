#!/usr/bin/env python3
'''
Deal with garfield files

File names:

  <S.S>_[col|ind]_[L|R]_[a|b].dat

S.S is electron shift in {0.0, 0.5, ..., 2.5} mm.
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
from wirecell.pcbro import holes

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

def dat2arrs(datfilename):
    #fninfo = parse_filename(datfilename)
    gen = wctgf.split_text_records(open(datfilename,'rb').read().decode())

    ret = defaultdict(list)
    for rec in gen:
        dat = wctgf.parse_text_record(rec)
        for k,v in dat.items():
            ret[k].append(v)
    arrs=dict()
    for k,v in ret.items():
        arrs[k] = numpy.asarray(v)
    return arrs

def dat2npz(datfilename, npzfile):
    arrs = dat2arrs(datfilename)
    numpy.savez(npzfile, **arrs)


def draw_file(datfilename, pdf_file):
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    import pylab

    fninfo = parse_filename(datfilename)
    print (fninfo)
    dat = dat2arrs(datfilename)
    
    wrp = dat['wire_region_pos']
    wrp = wrp[::2,:]
    curs = dat['y']
    curs = curs[0::2,:] + curs[1::2,:]
    print(curs.shape)

    with PdfPages(pdf_file) as pdf:

        def final(tit,xtit='transverse [mm]',ytit='drift'):
            plt.title(tit)
            if xtit: plt.xlabel(xtit)
            if ytit: plt.ylabel(ytit)
            pdf.savefig(plt.gcf())
            plt.close();
            
        hole_depth = 3.2

        pylab.subplot(aspect='equal');
        ax = plt.gcf().gca()
        for ind,(x,y) in enumerate(wrp):
            ax.add_artist(plt.Circle((x,y),0.15/2.0, fill=False))
            if ind < 10:
                vmin, vmax = numpy.min(curs[ind]), numpy.max(curs[ind])
                tot = numpy.sum(curs[ind]) * 100 * units.us / units.eplus
                lab = '[%d] %.1e < %.1e (%.1f)'%(ind,vmin,vmax,tot)
                tx = x
                ty = (2+ind)*0.25
                if y > hole_depth/2:
                    ty = hole_depth - ty
                plt.text(tx,ty, lab, fontsize=8)
        plt.plot([float(fninfo['dist'])],[3.5], marker="o")
        plt.plot([i*0.5 for i in range(6)],[3.5]*6, linewidth=0, marker="x")
        plt.plot((-1,-1), (0.0,hole_depth), color='blue')
        plt.plot((+1,+1), (0.0,hole_depth), color='blue')
        plt.ylim(-0.2,4.0)
        half_width=5.0
        plt.xlim(-half_width, half_width)
        final('micro wires {filename}'.format(**fninfo))
        


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
        '''Return a collection of responses over the span as 2D array.  

        Each row is a one response on a micro-wire.  Rows are ordered
        same as the span.

        The plane is the name ('ind' or 'col').  Radius is given as a
        float (in system of units) or more exactly as string
        representation in mm (eg '0.5') and must be from the set of
        radial impact positions covered by the loaded files.  Span is
        given as a pair of floating point numbers (in system of units)
        which are compared against micro-wire center positions.

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
        if span[1] < span[0]:
            span[0],span[1] = span[1],span[0]
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

        self.planes = dict(col = holes.Collection(),
                           ind = holes.Induction())

    def wire_region_pos(self, plane, snum):
        'Return position of strip'
        pl = self.ripem.plane[plane]
        y = pl.xpos             # longitiduinal drift direction
        x = snum * 5.0*units.mm # transverse direction
        return (x,y)

    @property
    def ticks(self):
        'Sample time of response function'
        return self.ripem.ticks

    @property
    def tstart(self):
        return self.ripem.ticks[0]
    @property
    def period(self):
        return self.ripem.ticks[1] - self.ripem.ticks[0]

    def response(self, plane, strip, sip, slices=[0,1]):
        '''
        Return response function for plane/strip and impact on one slice or average over slices.
        '''
        pholes = self.planes[plane];
        res = list()
        for slc in slices:
            #print (f'plane:{plane} strip:{strip} slc:{slc} sip:{sip}')
            sipobj = pholes.Sip(strip, slc, sip)
            for wr in sipobj.wirs:
                r = self.ripem.responses(plane, sipobj.rip, wr)
                if len(r.shape) != 2:
                    print(f'No response for plane:{plane} rad:{sipobj.rip} span:{wr}')
                    continue
                assert(r.shape[0])
                r = r.sum(axis=0)
                res.append(r)
        res = numpy.asarray(res)
        res = res.sum(axis=0)
        res /= len(slices)
        #print (f'plane:{plane} res.shape:{res.shape} res.size:{res.size}')
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

    def inschema(self, speed, origin, uslices=[0], vslices=[1], wslices=[0,1]):
        '''
        Return self as schema object
        wirecell.sigproc.response.schema.FieldResponse.

        The available strategy:
        - None :: u = v
        - "slice" :: u=slice1, v=slice2

        Support when we have it:
        - "hole" :: u=small hole, v=large hole
        '''
        from wirecell.sigproc.response.schema import FieldResponse, PlaneResponse, PathResponse
        
        def paths(pname, slices):
            ret = list()
            for istrip in range(-5,6):
                for isip in range(6):
                    sip = -2.5 + isip*0.5*units.mm
                    pos = self.wire_region_pos(pname, istrip)
                    pitchpos = float(pos[0]) + sip
                    res = self.response(pname, istrip, sip, slices)
                    pr = PathResponse(res, pitchpos, 0.0)
                    #print(f'{pname} strip:{istrip} sip#:{isip} sip:{sip} ppos:{pitchpos}')
                    ret.append(pr)
            return ret

        anti_drift_axis = (1.0, 0.0, 0.0)
        return FieldResponse(
            [PlaneResponse(paths("ind", uslices), 0, 3.2*units.mm, 5.0*units.mm),
             PlaneResponse(paths("ind", vslices), 1, 3.2*units.mm, 5.0*units.mm),
             PlaneResponse(paths("col", wslices), 2, 0.0*units.mm, 5.0*units.mm)],
            anti_drift_axis,
            origin, self.tstart, self.period, speed)



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

            for isip in range(6):
                sip = isip*0.5*units.mm

                # strategies only affect induction
                pos = self.wire_region_pos("col", istrip)
                ## RF.pos is (wirepos, pitchpos), pitchpos is relative to wire zero

                #print(f'strip:{istrip} sip#:{isip} sip:{sip} pos:{pos}')
                res = self.response("col", istrip, sip, [0,1])
                rf = RF("w", istrip, (0.0, pos[0]), ls, res, sip)
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

            
