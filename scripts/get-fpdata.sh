#!/bin/bash
set -e
set -x

# download data from FP's dropbox and fix as needed.

outdir=${PCBRO_DATADIR:-/home/bv/work/pcbro}/fp

mkdir -p $outdir
cd $outdir

if [ ! -s dv-2000v-h2mm5.zip ] ; then
    wget -O dv-2000v-h2mm5.zip 'https://www.dropbox.com/sh/tfbgqrebc94ia51/AAD5Dlq8chzs2aQIOfuryXMDa/DV-2000V-h2mm5?dl=0'
fi
if [ ! -s dv-2000v-h2mm0.zip ] ; then
    wget -O dv-2000v-h2mm0.zip 'https://www.dropbox.com/sh/tfbgqrebc94ia51/AACnJuFqgL_-HSo4699c4JQ8a/DV-2000V-h2mm0?dl=0'
fi
if [ ! -s dv-2000v.zip ] ; then
    wget -O dv-2000v.zip 'https://www.dropbox.com/sh/dh5ijin1bp0q00o/AABg8OC3p3WzZwJaarrmRFura?dl=0'
fi

for one in dv-2000v dv-2000v-h2mm0 dv-2000v-h2mm5
do
    if [ -d "$one" ] ; then
        echo "already unpacked $one"
        continue
    fi
    mkdir "$one"
    cd "$one"
    unzip "../${one}.zip" || true # zip complains 
    chmod -x *
    cd -
done

# these do not have any induction, take from dv-2000v
for one in dv-2000v-h2mm0 dv-2000v-h2mm5
do
    if [ -f "$one/induction-from-dv-2000" ] ; then
        echo "already fixed $one"
        continue
    fi
    cd "$one"
    rm -f fort.1??
    cp ../dv-2000v/fort.1?? .
    touch induction-from-dv-2000
    cd -
done

for one in dv-2000v dv-2000v-h2mm0 dv-2000v-h2mm5
do
    if [ -s "${one}-fixed.tgz" ] ; then
        echo "already have ${one}-fixed.tgz"
        continue
    fi
    tar -czf "${one}-fixed.tgz" "$one"
done
