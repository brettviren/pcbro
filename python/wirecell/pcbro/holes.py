from collections import defaultdict, namedtuple
import numpy

# sip:strip-impact-position.  in set {0.0,0.5,1.0,1.5,2.0,2.5}
# rip:radial-impact-position.  in set {0.0, 0.2, 0.3,...}
# cen:circle-center-position relative to strip center line
# dir:relative direction: +/- 1.
# wir:wire integration ranges (strictly postive)
Sip = namedtuple("Sip","sip rip cen dir wir")
Slice = namedtuple("Slice", "slcnum sips")
Strip = namedtuple("Strip", "name slices")
Plane = namedtuple("Plane", "pname strips")

planes = dict(                  # planes
    col = Plane("col", [        # strips
        Strip("even", [         # slices
            Slice(0, [          # sips
                #   sip, rip,  cen, dir, wir
                Sip(0.0, 0.8, -0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(+1.0, +2.3), (-1.0, -1.7)])),
                Sip(0.5, 1.3, -0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(+1.0, +2.3), (-1.0, -1.7)])),
                Sip(1.0, 1.5,  2.5, -1,
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (+4.3, +5.0)])),
                Sip(1.5, 1.0,  2.5, -1,
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (+4.3, +5.0)])),
                Sip(2.0, 0.5,  2.5, -1, 
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (+4.3, +5.0)])),
                Sip(2.5, 0.0,  2.5, -1,
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (+4.3, +5.0)])),
            ]),
            Slice(1, [
                Sip(0.0, 0.8, 0.8, -1,
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (-1.0, -1.7)])),
                Sip(0.5, 0.3, 0.8, -1,
                    lambda s: +5.0*s + numpy.asarray([(+1.0, +2.3), (-1.0, -1.7)])),
                Sip(1.0, 0.2, 0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(-1.0, -2.3), (+1.0, +1.7)])),
                Sip(1.5, 0.7, 0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(-1.0, -2.3), (+1.0, +1.7)])),
                Sip(2.0, 1.2, 0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(-1.0, -2.3), (+1.0, +1.7)])),
                Sip(2.5, 1.7, 0.8, +1,
                    lambda s: -5.0*s + numpy.asarray([(-1.0, -2.3), (+1.0, +1.7)])),
            ]),
        ]),                     # even

        Strip("oddpos", [
            Slice(0, [
                #   sip, rip,  cen, wir
                Sip(0.0, 0.8, 0.8, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+4.3, +5.6), (+7.6, 8.3)])),
                Sip(0.5, 0.3, 0.8, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+4.3, +5.6), (+7.6, 8.3)])),
                Sip(1.0, 0.2, 0.8, +1,
                    lambda s: -5.0*(s-1) + numpy.asarray([(-4.3, -5.6), (-7.6, -8.3)])),
                Sip(1.5, 0.7, 0.8, +1,
                    lambda s: -5.0*(s-1) + numpy.asarray([(-4.3, -5.6), (-7.6, -8.3)])),
                Sip(2.0, 1.2, 0.8, +1,
                    lambda s: -5.0*(s-1) + numpy.asarray([(-4.3, -5.6), (-7.6, -8.3)])),
                Sip(2.5, 1.7, 0.8, +1,
                    lambda s: -5.0*(s-1) + numpy.asarray([(-4.3, -5.6), (-7.6, -8.3)])),
            ]),
            Slice(1, [
                Sip(0.0, 0.8, -0.8, +1, 
                    lambda s: -5.0*(s-1) + numpy.asarray([(-1.7, -2.4), (-4.4, -5.7)])),
                Sip(0.5, 1.3, -0.8, +1,
                    lambda s: -5.0*(s-1) + numpy.asarray([(-1.7, -2.4), (-4.4, -5.7)])),
                Sip(1.0, 1.5,  2.5, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+5.0, +5.7), (+7.7, +9.0)])),
                Sip(1.5, 1.0,  2.5, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+5.0, +5.7), (+7.7, +9.0)])),
                Sip(2.0, 0.5,  2.5, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+5.0, +5.7), (+7.7, +9.0)])),
                Sip(2.5, 0.0,  2.5, -1,
                    lambda s: +5.0*(s-1) + numpy.asarray([(+5.0, +5.7), (+7.7, +9.0)])),
            ])]),

        Strip("oddneg", [
            Slice(0, [
                #   sip, rip,  cen, wir
                Sip(0.0, 0.8, 0.8, -1,
                    lambda s: +5.0*(s+1) + numpy.asarray([(-1.7, -3.4), (-4.4, -5.7)])),
                Sip(0.5, 0.3, 0.8, -1,
                    lambda s: +5.0*(s+1) + numpy.asarray([(-1.7, -3.4), (-4.4, -5.7)])),
                Sip(1.0, 0.2, 0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(+1.7, +3.4), (+4.4, +5.7)])),
                Sip(1.5, 0.7, 0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(+1.7, +3.4), (+4.4, +5.7)])),
                Sip(2.0, 1.2, 0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(+1.7, +3.4), (+4.4, +5.7)])),
                Sip(2.5, 1.7, 0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(+1.7, +3.4), (+4.4, +5.7)])),
            ]),
            Slice(1, [
                Sip(0.0, 0.8, -0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(4.3, 5.6), (7.6, 8.3)])),
                Sip(0.5, 1.3, -0.8, +1,
                    lambda s: -5.0*(s+1) + numpy.asarray([(4.3, 5.6), (7.6, 8.3)])),

                Sip(1.0, 1.5,  2.5, -1,
                    lambda s: 5.0*(s+1) + numpy.asarray([(-1.0, -2.3), (-4.3, -5.0)])),
                Sip(1.5, 1.0,  2.5, -1,
                    lambda s: 5.0*(s+1) + numpy.asarray([(-1.0, -2.3), (-4.3, -5.0)])),
                Sip(2.0, 0.5,  2.5, -1,
                    lambda s: 5.0*(s+1) + numpy.asarray([(-1.0, -2.3), (-4.3, -5.0)])),
                Sip(2.5, 0.0,  2.5, -1,
                    lambda s: 5.0*(s+1) + numpy.asarray([(-1.0, -2.3), (-4.3, -5.0)])),
            ])])]),
    ind = Plane("ind", [
        Strip("all", [
            Slice(0, [
                #   sip, rip,  cen, wir
                Sip(0.0, 0.0, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
                Sip(0.5, 0.5, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
                Sip(1.0, 1.0, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
                Sip(1.5, 1.5, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
                Sip(2.0, 2.0, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
                Sip(2.5, 2.5, 0.0, +1,
                    lambda s: -5.0*s + numpy.asarray([(1.0,2.5), (-1.0, -2.5)])),
            ]),
            Slice(1, [
                Sip(0.0, 2.5, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
                Sip(0.5, 2.0, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
                Sip(1.0, 1.5, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
                Sip(1.5, 1.0, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
                Sip(2.0, 0.5, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
                Sip(2.5, 0.0, 2.5, -1,
                    lambda s: 5.0*s + numpy.asarray([(1.0,2.5), (2.5, 4.0)])),
            ])])]))

def get_strip(plane, sname):
    for s in plane.strips:
        if s.name == sname:
            return s
    raise KeyError(f'no strip named "{sname}"')

def get_strips(plane):
    '''
    Return strips specs in order
    '''
    pd = planes[plane]
    if plane == "col":
        oddpos = get_strip(pd, "oddpos")
        oddneg = get_strip(pd, "oddneg")
        even = get_strip(pd, "even")
        return [oddneg, even, oddneg, even, oddneg,
                even,
                oddpos, even, oddpos, even, oddpos]
    only = get_strip(pd, "all")
    return [only] * 11


        
