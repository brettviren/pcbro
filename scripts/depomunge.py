#!/usr/bin/env python3
'''
Give me a NumpyDepoSaver file, I'll munge it to fit 50L
'''
import sys
import numpy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def plot(fname, depo, narrow=False):

    fig, axes = plt.subplots(nrows=3, ncols=2)

    s = 0.01

    for ind in [2,3,4]:
        if narrow:
            indet = numpy.abs(depo[ind]) < 150
            axes[0,0].scatter(depo[0][indet], depo[ind][indet], s=s)
        else:
            axes[0,0].scatter(depo[0], depo[ind], s=s)
    axes[0,0].set_title("vs time")

    xin = numpy.abs(depo[2]) < 150
    yin = numpy.abs(depo[3]) < 150
    zin = numpy.abs(depo[4]) < 150

    if narrow:
        axes[1,0].scatter(depo[3][zin],depo[2][zin], s=s)
        axes[1,0].set_title("x vs y")
        axes[1,0].grid()
        
        axes[0,1].scatter(depo[4][zin],depo[3][zin], s=s)
        axes[0,1].set_title("y vs z")
        axes[0,1].grid()
        
        axes[1,1].scatter(depo[4][zin],depo[2][zin], s=s)
        axes[1,1].set_title("x vs z")
        axes[1,1].grid()

    else:
        axes[1,0].scatter(depo[3],depo[2], s=s)
        axes[1,0].set_title("x vs y")
        axes[1,0].grid()
        
        axes[0,1].scatter(depo[4],depo[3], s=s)
        axes[0,1].set_title("y vs z")
        axes[0,1].grid()
        
        axes[1,1].scatter(depo[4],depo[2], s=s)
        axes[1,1].set_title("x vs z")
        axes[1,1].grid()

    axes[2,0].remove()
    axes[2,1].remove()

    ax1 = fig.add_subplot(3, 2, 5, projection='3d')    
    ax2 = fig.add_subplot(3, 2, 6, projection='3d')    


    ax1.scatter(depo[2],depo[3],depo[4], s=s)
    ax2.scatter(depo[2][zin],depo[3][zin],depo[4][zin], s=s)

    plt.savefig(fname)

    # with PdfPages(fname) as pdf:
    #     for ind in [1,2,3,4]:
    #         plt.scatter(depo[0], depo[ind])
    #         pdf.savefig(plt.gcf())
    #         plt.close()
            

in_file = sys.argv[1]
out_file = sys.argv[2]
plot_dir = sys.argv[3]

fp = numpy.load(in_file)
data = fp['depo_data_0']
info = fp['depo_info_0']

plot(f"{plot_dir}/depomunge-before.png", data, False)

# Center
bb = numpy.array([(0,380),(-150,150),(-150,150)])

cens = numpy.array([
    (900,1100,2900),        # track start
    (900,900,5000),        # smooth
    (700,400,12500),        # kink/m-e?
    (700,1000,3300),
    (1000,600,10000),
    (1100,800,7000),
])
center = cens[0]

print(center)

# move to time = 0
data[0] -= min(data[0])

data[2] -= center[0]
data[3] -= center[1]
data[4] -= center[2]

plot(f"{plot_dir}/depomunge-center.png", data, False)


# Rotate
from scipy.spatial.transform import Rotation as R
# At the track's start point it is going parallel to z-axis.
# We want it to be approximately diagonal in all axis.
# Rotate along x by 45deg 
rotx = R.from_rotvec(numpy.pi/4 * numpy.array([1, 0, 0]))
roty = R.from_rotvec(numpy.pi/4 * numpy.array([0, -1, 0]))

data[2:5] = roty.apply(rotx.apply(data[2:5].T)).T

plot(f"{plot_dir}/depomunge-rotate.png", data, False)

data[2] += 100

plot(f"{plot_dir}/depomunge-after.png", data, True)

numpy.savez(out_file, depo_data_0=data, depo_info_0=info)

