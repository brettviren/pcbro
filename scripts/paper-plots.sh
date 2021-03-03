#!/bin/bash

if [ -z "$1" ] ; then
    for n in 2D 3D
    do
        $0 $n
    done
    exit 0
fi


label="$1" ; shift
if [ "$label" = "2D" ] ; then   # 2.5D trick
    RESFILE=pcbro-response-avg.json.bz2
    sig_title="2.5D trick"
elif [ "$label" = "3D" ] ; then # FP's 3D->2D
    RESFILE=dv-2000v.json.bz2
    sig_title="3D->2D"
else
    echo "Unknown label: $label"
    echo "try 2D or 3D"
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
channels='0:64,64:128'
# cmap='viridis'
# cmap='plasma'
# cmap='bwr'
# cmap='prism'

# gray binary
for cmap in best  # bwr seismic viridis 
do
    outdir="plots/$cmap"
    mkdir -p $outdir

    common_args="-t $trigger --channels $channels"
    raw_cmap=$cmap
    sig_cmap=$cmap
    raw_args="--color-range=-512,0,512"
    sig_args="--color-range=-100,0,5000"
    if [ "$cmap" = "best" ] ; then
        raw_cmap=seismic
        sig_cmap=nipy_spectral
        raw_args="--color-range=-300,0,300"
        sig_args="--color-range=0,5000,20000 --mask-min=0"
    fi

    raw_ticks="--ticks 100:550 --tshift -12"
    sig_ticks="--ticks 100:550 --tshift +20"
    if [ "$label" = "3D" ] ; then
        sig_ticks="--ticks 0:450"
    fi

    for ext in png pdf
    do

        ## RAW
        wirecell-pcbro \
            evd2d $common_args \
            --title="Raw data from run $timestamp trigger {trigger}" \
            --color-unit="ADC from baseline" \
            --color-map $raw_cmap \
            $raw_args $raw_ticks \
            --baseline-subtract median \
            -o $outdir/raw-${TSDS}-${trigger}.$ext $RAWNPZ


        ## SIG
        wirecell-pcbro \
            evd2d $common_args \
            --title="Signals from run $timestamp trigger {trigger} ($sig_title)" \
            --color-map $sig_cmap \
            $sig_args $sig_ticks \
            -T gauss0 \
            -o $outdir/sig-${TSDS}-${trigger}-${label}.$ext $SIGNPZ
    done
done

