#!/bin/bash

# This script downloads field response calculations from Francesco's
# dropbox and ultimately converts to WCT format.

set -x

label="$1"
dburl="$2"
shift 2

zipfile="${label}.zip"
tarfile="${label}.tar"
spltnpz="${label}-splt.npz"

if [ -s "$zipfile" ] ; then
    echo "already have $zipfile"
else
    wget -O "$zipfile" "$dburl" || exit -1
fi

if [ -d "$label" ] ; then
    echo "already have $label dir"
else
    mkdir -p "$label"
    cd $label
    unzip ../$zipfile
    cd -
fi


if [ -s "$tarfile" ] ; then
    echo "already have $tarfile"
else
    tar -cf $tarfile $label
fi

if [ -s "$spltnpz" ] ; then
    echo "already have $spltnpz"
else
    wirecell-pcbro fpstrips-tar2spltnpz "$tarfile" "$spltnpz"
fi

for pl in imp col
do
    spltpdf="${label}-splt-${pl}.pdf"
    if [ -s "$spltpdf" ] ; then
        echo "already have $spltpdf"
    else
        wirecell-pcbro fpstrips-draw-splt -p "$pl" "$spltnpz" "$spltpdf"
    fi
done
