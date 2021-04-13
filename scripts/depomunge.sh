#!/bin/bash

set -e
set -x

mydir=$(dirname $(realpath $BASH_SOURCE))

resp=$HOME/work/pcbro/resp/dv-2000v-h2mm0.json.bz2
hwyds=$HOME/work/pcbro/haiwang-depos.npz

outdir=$HOME/work/pcbro/depomunge
mkdir -p $outdir

depos=$outdir/munged-depos.npz
rframe=$outdir/munged-frame-sim.npz
sframe=$outdir/munged-frame-ssp.npz

rdisp=$outdir/munged-frame-sim.png
sdisp=$outdir/munged-frame-ssp.png

rm -rf $depos $rframe $sframe
$mydir/depomunge.py $hwyds $depos
mv depomunge-*.png $outdir/

rm -f $rframe
wire-cell \
          -A depofile=$depos \
          -A framefile=$rframe \
          -A resps_file=$resp \
          -c cfg/cli-npz-sim-npz.jsonnet
if [ ! -s $rframe ] ; then
    echo "Failed to make $rframe"
    exit
fi
rm -f $sframe
wire-cell \
          -A depofile=$depos \
          -A framefile=$sframe \
          -A resps_file=$resp \
          -A do_sigproc=yes \
          -c cfg/cli-npz-sim-npz.jsonnet
if [ ! -s $sframe ] ; then
    echo "Failed to make $sframe"
    exit
fi

wirecell-pcbro \
    evd2d \
    --ticks='0:645' \
    --color-range='-300,0,300' \
    --color-map=seismic \
    --baseline-subtract=median \
    -t 0 -T orig0 -o $rdisp $rframe

wirecell-pcbro \
    evd2d \
    --color-map=cubehelix \
    --color-range='0,2500,20000' \
    --mask-min=0 \
    --ticks='0:800' \
    -t 0 -T gauss0 \
    -o $sdisp $sframe



