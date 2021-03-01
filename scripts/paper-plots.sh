#!/bin/bash

label="$1" ; shift
if [ "$label" = "2.5D" ] ; then
    RESFILE=pcbro-response-avg.json.bz2
elif [ "$label" = "FP" ] ; then
    RESFILE=dv-2000v.json.bz2
else
    echo "Unknown label: $label"
    echo "try 2.5D or FP"
    exit -1
fi

set -x

mkdir -p "$label"


TSDS=159048405892               # deciseconds
TS=1590484058
timestamp=$(TZ=CET date --date=@"${TS}" +"%Y-%m-%d %H:%M:%S")
BINFILE="$HOME/work/pcbro/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_${TSDS}.bin"


RAWNPZ="$label/raw-$TS.npz"
SIGNPZ="$label/sig-$TS.npz"

if [ ! -s "$RAWNPZ" ] ; then 
    wire-cell \
        -A infile=$BINFILE \
        -A outfile=$RAWNPZ \
        -c cfg/cli-bin-npz.jsonnet
fi
if [ ! -s "$SIGNPZ" ] ; then
    wire-cell \
        -A resp=$RESFILE \
        -A infile=$BINFILE \
        -A outfile=$SIGNPZ \
        -c cfg/cli-bin-sp-npz.jsonnet
fi


trigger=31
ticks='100:500'
channels='0:64,64:128'
# cmap='viridis'
# cmap='plasma'
# cmap='bwr'
# cmap='prism'

for cmap in bwr viridis
do
    outdir="plots/$label/$cmap"
    mkdir -p $outdir

    common_args="-t $trigger --ticks $ticks --color-map $cmap --channels $channels"

    for ext in png pdf
    do

        ## RAW
        wirecell-pcbro \
            evd2d $common_args \
            --title="Raw data from run $timestamp trigger {trigger}" \
            --color-unit="ADC from baseline" \
            --color-range='-512,0,512' \
            --baseline-subtract median \
            -o $outdir/raw-${TSDS}-${trigger}.$ext $RAWNPZ


        ## SIG
        wirecell-pcbro \
            evd2d $common_args \
            --title="Signals from run $timestamp trigger {trigger}" \
            --tshift=38 \
            --color-range='-100,0,5000' \
            -T gauss0 \
            -o $outdir/sig-${TSDS}-${trigger}.$ext $SIGNPZ
    done
done

