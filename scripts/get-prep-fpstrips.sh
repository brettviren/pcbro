#!/bin/bash

# This script downloads field response calculations from Francesco's
# dropbox and ultimately converts to WCT format.

set -x

label="$1"
dburl="$2"
shift 2

zipfile="${label}.zip"
fpnpzfile="${label}-fp.npz"
fppdffile="${label}-fp.pdf"
wctnpzfile="${label}-wct.npz"
jsonfile="${label}.json.bz2"
pltfile="docs/${label}.png"

if [ -s "$zipfile" ] ; then
    echo "already have $zipfile"
else
    wget -O "$zipfile" "$dburl" || exit -1
fi

if [ -s "$fpnpzfile" ] ; then
    echo "already have $fpnpzfile"
else
    wirecell-pcbro fpstrips-fp-npz "$zipfile" "$fpnpzfile"
fi

if [ -s "$fppdffile" ] ; then
    echo "already have $fppdffile"
else
    wirecell-pcbro fpstrips-draw-fp $fpnpzfile $fppdffile
fi

if [ -s "$wctnpzfile" ] ; then
    echo "already have $wctnpzfile"
else
    wirecell-pcbro fpstrips-wct-npz "$fpnpzfile" "$wctnpzfile"
fi

if [ -s "$jsonfile" ] ; then
    echo "already have $jsonfile"
else
    wirecell-pcbro convert-fpstrips "$zipfile" "$jsonfile"
fi

if [ -s "$pltfile" ] ; then
    echo "already have $pltfile"
else
    wirecell-sigproc plot-response --region 0 --trange 0,120 --reflect "$jsonfile" "$pltfile"
fi



