#!/bin/bash
# hacky script to run depomunge.py and process the resulting depos
# through wire-cell and wirecell-pcbro plotting.  This script is mean
# to run from snakemake (or direct cli).

set -e
set -x

mydir=$(dirname $(realpath $BASH_SOURCE))

respname=${1:-dv-2000v-h2mm0}

# Note, these patterns must mach Snakefile!

resp=$HOME/work/pcbro/resp/$respname.json.bz2
hwyds=$HOME/work/pcbro/haiwang-depos.npz

outdir=$HOME/work/pcbro/depomunge/$respname
mkdir -p $outdir
pltdir=$HOME/work/pcbro/plots/depomunge/$respname
mkdir -p $pltdir

depos=$outdir/munged-depos.npz
rframe=$outdir/munged-frame-sim.npz
sframe=$outdir/munged-frame-ssp.npz

rdisp=$pltdir/munged-frame-sim.png
sdisp=$pltdir/munged-frame-ssp.png

rm -rf $depos $rframe $sframe
$mydir/depomunge.py $hwyds $depos $pltdir/

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



