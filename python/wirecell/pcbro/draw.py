import numpy
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pylab

def holes_planegeometry(pg, pdf_file="pcbro-holes.pdf",
                        slices=[0,1], strips=range(-5,6), nsips=6):
    '''
    Make some drawings with a holes.PlaneGeometry implementations
    '''
    imp = 0.5*pg.wid / (nsips-1)

    sips = [-0.5*pg.wid + imp*n for n in range(6)]

    with PdfPages(pdf_file) as pdf:
        pylab.subplot(aspect='equal');
        ax = plt.gcf().gca()

        circs = list()
        marks = list()
        clines = list()

        strip_spacing = pg.sep*5
        slice_spacing = pg.sep*2
        range_spacing = 0.4*pg.sep
        sip_spacing = 0.1*pg.sep

        ghost_circs = list()
        for strip in set([abs(s) for s in strips]):
            strip_x = abs(strip)*strip_spacing            
            for slc in slices:
                for isip,sipy in enumerate(sips):
                    for gstrip in strips: #[-1,0,1]:
                        sip = pg.Sip(gstrip, slc, sipy)
                        slc_x = slc*slice_spacing
                        cx = slc_x + strip_x
                        cy = sip.cen + gstrip*pg.wid
                        ghost_circs.append((cx,cy))

        for strip in strips:
            strip_x = abs(strip)*strip_spacing
            for slc in slices:
                slc_x = slc*slice_spacing
                for isip,sipy in enumerate(sips):
                    sip = pg.Sip(strip, slc, sipy)
                    cline_y = strip*pg.wid
                    clines.append(cline_y)
                    cx = slc_x + strip_x
                    cy = sip.cen + cline_y
                    circs.append((cx,cy))

                    for i,(d,w) in enumerate(zip(sip.dirs,sip.wirs)):
                        side = -1
                        if i: side = +1
                        # the "d" is the relative direction between
                        # GARFIELD and real geometry.  The wire ranges
                        # "w" are measured w.r.t. ciricle center in
                        # GARFIELD geometry.  "wr" is then the ranges
                        # in real geometry.
                        wr = d*w+cy
                        marks.append(((cx + side*(range_spacing + isip*sip_spacing), cline_y + sip.sip), d, wr))

        for circ in set(ghost_circs):
            circle = plt.Circle(circ, pg.rad, color="gray", linewidth=0.0)
            ax.add_artist(circle)
        for circ in set(circs):
            circle = plt.Circle(circ, pg.rad, linewidth=0.0)
            ax.add_artist(circle)

        for mark in marks:
            (x,y),d,wr = mark
            marker="1"
            if d > 0:
                marker="2"
            plt.plot(x, y, marker, linewidth=0.1, color="black")
            plt.plot((x,x), wr, solid_capstyle="butt")

        xymin = numpy.min(circs, axis=0) - numpy.array([strip_spacing,pg.wid])
        xymax = numpy.max(circs, axis=0) + numpy.array([strip_spacing,pg.wid])

        largs=dict(linewidth=0.1)

        for cline in set(clines):
            plt.plot((xymin[0], xymax[0]), (cline, cline),
                     color="gray", linestyle="dotted", **largs)
            plt.plot((xymin[0], xymax[0]), (cline+0.5*pg.wid, cline+0.5*pg.wid),
                     color="black", linestyle="solid", **largs)
            plt.plot((xymin[0], xymax[0]), (cline-0.5*pg.wid, cline-0.5*pg.wid),
                     color="black", linestyle="solid", **largs)

        plt.xlim(xymin[0], xymax[0])
        plt.ylim(xymin[1], xymax[1])

        pdf.savefig(plt.gcf())
        plt.close();
