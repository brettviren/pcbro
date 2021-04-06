#!/bin/bash

set -e
set -x

tshift=0
resp=/home/bv/work/pcbro/tshift/resp/dv-2000v-h2mm5-$tshift.json.bz2
ssp=/home/bv/dev/pcbro/cfg/cli-ssp-npz.jsonnet
sim=/home/bv/dev/pcbro/cfg/cli-sim-npz.jsonnet

wire-cell -A resps_file=$resp -A outfile=sim.npz -c $sim
wire-cell -l stdout -L debug -A resps_file=$resp -A outfile=ssp.npz -c $ssp

wirecell-pcbro \
    evd2d -t 0 --channels '0:64,64:128' \
    --title="Sim raw trigger 0 (dv-2000v-h2mm5-$tshift)" \
    --color-unit='ADC from baseline' \
    --color-map=seismic \
    --color-range='-300,0,300' \
    --ticks='0:1000' \
    --baseline-subtract=median \
    -T orig0 \
    -o sim.png sim.npz

wirecell-pcbro \
    evd2d -t 0 --channels '0:64,64:128' \
    --title="Sim sigproc trigger 0 (dv-2000v-h2mm5-$tshift)" \
    --color-map=cubehelix \
    --color-range='0,2500,20000' \
    --mask-min=0 \
    -T gauss0 \
    --ticks '0:1000' \
    -o ssp.png ssp.npz

