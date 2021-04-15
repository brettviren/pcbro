#!/bin/bash

# This script prepares input files from FP by downloading them from
# dropbox, doing some cosmetic fixes and creating tar files.
#
# File names and locations are matched to what the pcbro/Snakefile
# expects.

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
# if [ ! -s reference3views-v2.zip ] ; then
#     wget -O reference3views-v2.zip 'https://www.dropbox.com/sh/tfbgqrebc94ia51/AADNer78R-ff3MfbR5RPpRLoa?dl=0'
#     echo b7d23d91bd9671a202978f926dc84d09
#     md5sum reference3views-v2.zip
# fi
if [ ! -s reference3views-v3.zip ] ; then
    wget -O reference3views-v3.zip 'https://www.dropbox.com/sh/tfbgqrebc94ia51/AADNer78R-ff3MfbR5RPpRLoa?dl=0'
    echo 0d61451013bec692aec2abdfa08f33de
    md5sum reference3views-v3.zip
    # fixme: run md5sum in mode to actually check this!
fi

for one in dv-2000v dv-2000v-h2mm0 dv-2000v-h2mm5 reference3views-v3
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

# for one in reference3views-v2
# do
#     # the zip holds some really messed up permissions
#     chmod -R 755 $one
#     chmod 444 $one/*/*/fort.*
#     cd $one/Reference3views
#     for pln in collection induction1 induction2
#     do
#         if [ -f "../${pln}.tar" ] ; then
#             echo "$pln.tar exists"
#             continue
#         fi
#         tar -cf "${pln}.tar" $pln
#         mv "${pln}.tar" ../
#     done
#     cd -
# done
# Two sets, repeating 30deg: col-


for one in reference3views-v3
do
    # chmod -R 755 $one
    # chmod 444 $one/*/*/fort.*
    cd $one/Reference3views
    for hole in 2.3 2.4
    do
        hname="h$(echo $hole | sed -e 's/\./mm/')"
        # this name must match what is used in snakefile
        setdir="$outdir/reference3views-${hname}"
        mkdir -p "$setdir"
        for pln in collection induction1 induction2
        do
            tarball="${setdir}/${pln}.tar"
            if [ -f "$tarball" ] ; then
                echo "$tarball exists"
                continue
            fi
            tar -cf "${tarball}" ${pln}-${hole}-?.??
        done
    done
    cd -
done
