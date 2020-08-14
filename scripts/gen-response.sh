#!/bin/bash

## made from select files from Yichen's Garfield output
# tar -cvf garfield-pcb.tar \
#   pcb_try/*_ind_*.dat \
#   pcb_try_add/{0.2,0.3,0.7,0.8,1.2,1.3,1.7}_col_*.dat \
#   pcb_try/{0.0,0.5,1.0,1.5}_col_*.dat
garfield_tarfile=${1:-$HOME/work/pcbro/fields/garfield-pcb.tar}
srcdir=$(dirname $(dirname $(realpath $BASH_SOURCE)))
cfgdir="$srcdir/cfg"

if [ -f pcbro-response-avg.json.bz2 ] ; then
    echo "file exists, no regen"
    echo pcbro-response-avg.json.bz2
else
    wirecell-pcbro convert-garfield $garfield_tarfile
fi

for n in pcbro-response-*.json.bz2
do
    base=$(basename $n .json.bz2)
    wirecell-sigproc plot-response --region 2.5 --trange  0,85 $n ${base}.png || exit 1
    wirecell-sigproc plot-response --region 2.5 --trange  55,85 $n ${base}-zoom.png || exit 1
done

tar -cf pcbro-response-latest.tar pcbro-response-*.{json.bz2,png}
cp pcbro-response-*.png docs/
cp pcbro-response-*.json.bz2 cfg/

# rsync pcbro-response-latest.tar hierocles.bnl:public_html/tmp/pcbro/
