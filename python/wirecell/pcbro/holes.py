#!/usr/bin/env python3
'''Describe the geometry in terms of slices and strips and planes and
strip impact positions and ranges of integration.

Note: this file assumes all literal distance values are in implicitly
stated wirecell.units base unit for length (mm).

'''

from collections import defaultdict, namedtuple
import numpy

# sip:strip-impact-position relative to strip center line. Eg, in set
# {-0.0,-0.5,-1.0,-1.5,-2.0,-2.5}
#
# rip:radial-impact-position relative to hole center.  Strictly
# non-negative.
#
# cen:circle-center-position relative to local strip center line.
#
# dirs:relative direction between real space and GARFIELD: +/- 1.
#
# wirs:wire integration ranges (in GARFIELD space)
Sip = namedtuple("Sip","sip rip cen dirs wirs")
Slice = namedtuple("Slice", "slcnum sips")
Strip = namedtuple("Strip", "name slices")
Plane = namedtuple("Plane", "pname strips")

class PlaneGeometry(object):

    def hcbss(self): pass

    def holes(self, strip, slc):
        '''
        Return list of hole centers for given strip and slice
        '''
        return numpy.unique(self.hcbss()[strip%2, slc%2])
                             

    def filled0(self, slc):
        '''
        Return Nx2 array giving filled in conductor regions of slice in strip0
        '''
        holes = self.holes(0, slc)

        edges = list()
        for cen in holes:
            edges += [cen-self.rad, cen+self.rad]
        edges = [e for e in edges if abs(e) < 0.5*self.wid]

        for strip_edge in [0.5*self.wid, -0.5*self.wid]:
            if numpy.all([abs(strip_edge-h) > self.rad for h in holes]):
                edges.append(strip_edge)

        edges.sort()
        return numpy.array(edges).reshape((len(edges)//2, 2))

    def microwire_ranges(self, cen, strip, slc):
        '''Return the range of "micro wires" for a hole centered at cen
        relative to centerline of strip for slice slc.  Ranges are
        signed distances relative to the hole center repreresenting
        real geometry (no GARFIELD flip)
        '''
        # strip 0 center to hole center
        s0c2h = strip * self.wid + cen
        return self.filled0(slc) - s0c2h


    def Sip(self, strip, slc, sip):
        '''
        Return a Sip object for the hole nearest the sip on strip/slc.
        '''
        holes = self.holes(strip, slc);
        cen = holes[numpy.argmin(numpy.abs(sip-holes))]
        rips = sip - cen        # radial impact position, signed
        rip = abs(rips)

        rip_sign = rips == rip

        dirs = list()
        wirs = list()

        # if impact is on the same side of the circle diameter as the
        # range, then it stays as-is.  O.w. a sign flip is needed to
        # map GARFIELD space to physical direction along the slice.
        for mwr in self.microwire_ranges(cen, strip, slc):
            mwr_sign = mwr == numpy.abs(mwr)
            flip = 1
            if rip_sign == mwr_sign.all():
                flip = -1
            dirs.append(flip)
            wirs.append(flip*mwr)
        return Sip(sip,rip,cen,numpy.asarray(dirs),numpy.asarray(wirs))
            

class Collection(PlaneGeometry):
    coff = 0.8      # mm, distance from centerline to full hole center
    wid = 5.0       # mm, width of strip, inc edge gap
    rad = 1.0       # mm, radius of hole

    @property
    def sep(self):
        'full width of strip including gaps in mm'
        return self.wid/2.0

    def hcbss(self):
        '''Return 2x2xN matrix of hole centers relative to centerline.

        Matrix is shaped strip x slice x hole.
        '''
        return numpy.asarray([ [[-self.coff, 0.5*self.wid],  # strip0,slc0
                                [-0.5*self.wid, self.coff]], # strip0,slc1
                               [[-0.5*self.wid, self.coff],  # strip1,slc0
                                [-self.coff, 0.5*self.wid]]  # strip1,slc1
                              ])


class Induction(PlaneGeometry):

    wid = 5.0       # mm, full width of strip including gaps
    rad = 1.0       # mm, radius of hole
    
    @property
    def sep(self):
        'full width of strip including gaps in mm'
        return self.wid/3.0

    def hcbss(self):
        # double the center circle to make proper matrix.  Other code
        # needs to protect against this tuplication!
        return numpy.asarray([ [[0.0,0.0], [-0.5*self.wid, +0.5*self.wid]], # strip0
                               [[0.0,0.0], [-0.5*self.wid, +0.5*self.wid]]  # strip1
                              ])

def get_strips(plane):

    if plane == "col":
        geom = Collection()
    elif plane == "ind":
        geom = Induction()
    else:
        raise ValueError(f'unknown plane {plane}')

    strips = list()
    for strip in range(-5,6):
        slices=list()
        for slc in [0,1]:
            sips = [geom.Sip(strip, slc, -2.5 * 0.5*n) for n in range(6)]
            slices.append(Slice(slc, sips))
        if strip < 0:
            sname=f's{strip}'
        elif strip > 0:
            sname=f's+{strip}'
        else:
            sname='s00'
        strips.append(Strip(sname ,slices))
    return strips

