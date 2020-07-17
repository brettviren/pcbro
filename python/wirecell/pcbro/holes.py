from collections import defaultdict, namedtuple

Sip = namedtuple("Sip","sip rip cen")
Slice = namedtuple("Slice", "slcnum sips")
Strip = namedtuple("Strip", "name slices")
Plane = namedtuple("Plane", "pname strips")

planes = dict(                  # planes
    col = Plane("col", [        # strips
        Strip("even", [         # slices
            Slice(0, [          # sips
                Sip(0.0, +0.8, -0.8),
                Sip(0.5, +1.3, -0.8),
                Sip(1.0, -1.5,  2.5),
                Sip(1.5, -1.0,  2.5),
                Sip(2.0, -0.5,  2.5),
                Sip(2.5,  0.0,  2.5),
            ]),
            Slice(1, [
                Sip(0.0, -0.8, 0.8),
                Sip(0.5, -0.3, 0.8),
                Sip(1.0, +0.2, 0.8),
                Sip(1.5, +0.7, 0.8),
                Sip(2.0, +1.2, 0.8),
                Sip(2.5, +1.7, 0.8),
            ]),
        ]),
        Strip("odd", [
            Slice(0, [
                Sip(0.0, -0.8, 0.8),
                Sip(0.5, -0.3, 0.8),
                Sip(1.0, +0.2, 0.8),
                Sip(1.5, +0.7, 0.8),
                Sip(2.0, +1.2, 0.8),
                Sip(2.5, +1.7, 0.8),
            ]),
            Slice(1, [
                Sip(0.0, +0.8, -0.8),
                Sip(0.5, +1.3, -0.8),
                Sip(1.0, -1.5,  2.5),
                Sip(1.5, -1.0,  2.5),
                Sip(2.0, -0.5,  2.5),
                Sip(2.5,  0.0,  2.5),
            ])])]),
    ind = Plane("ind", [
        Strip("all", [
            Slice(0, [
                Sip(0.0, 0.0, 0.0),
                Sip(0.5, 0.5, 0.0),
                Sip(1.0, 1.0, 0.0),
                Sip(1.5, 1.5, 0.0),
                Sip(2.0, 2.0, 0.0),
                Sip(2.5, 2.5, 0.0),
            ]),
            Slice(1, [
                Sip(0.0, -2.5, 2.5),
                Sip(0.5, -2.0, 2.5),
                Sip(1.0, -1.5, 2.5),
                Sip(1.5, -1.0, 2.5),
                Sip(2.0, -0.5, 2.5),
                Sip(2.5,  0.0, 2.5),
            ])])]))

        
