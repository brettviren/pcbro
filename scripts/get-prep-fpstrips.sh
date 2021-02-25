#!/bin/bash

# This script downloads field response calculations from Francesco's
# dropbox and ultimately converts to WCT format.

set -x

label="$1"
dburl="$2"
shift 2

zipfile="${label}.zip"
fidnpzfile="${label}-fid.npz"
fidpdffile="${label}-fid.pdf"

if [ -s "$zipfile" ] ; then
    echo "already have $zipfile"
else
    wget -O "$zipfile" "$dburl" || exit -1
fi

if [ -s "$fidnpzfile" ] ; then
    echo "already have $fidnpzfile"
else
    wirecell-pcbro fpstrips-zip2npz "$zipfile" "$fidnpzfile"
fi

if [ -s "$fidpdffile" ] ; then
    echo "already have $fidpdffile"
else
    wirecell-pcbro fpstrips-draw-fids $fidnpzfile $fidpdffile
fi

