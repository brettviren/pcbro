#!/bin/bash

## made from select files from Yichen's Garfield output
# tar -cvf garfield-pcb.tar \
#   pcb_try/*_ind_*.dat \
#   pcb_try_add/{0.2,0.3,0.7,0.8,1.2,1.3,1.7}_col_*.dat \
#   pcb_try/{0.0,0.5,1.0,1.5}_col_*.dat
garfield_tarfile=${1:-$HOME/work/pcbro/fields/garfield-pcb.tar}
srcdir=$(dirname $(dirname $(realpath $BASH_SOURCE)))
cfgdir="$srcdir/cfg"

resp () {
    echo "pcbro-response-${1}.json.bz2"
}

gar2wct () {
    local out=$1 ; shift
    local u=$1 ; shift
    local v=$1 ; shift
    local w=$1 ; shift

    out="$cfgdir/$out"

    if [ -f $out ] ; then
        echo "file exists: $out"
        return
    fi
    echo "generating: $out"
    wirecell-pcbro convert-garfield -U $u -V $v -W $w $garfield_tarfile $out || exit 1
}

plot () {
    local inf=$1 ; shift
    inf="$cfgdir/$inf"

    local out=$(basename $inf .json.bz2)

    out="$cfgdir/$out"

    local out1="${out}.png"
    wirecell-sigproc plot-response --region 2.5 --trange  0,85 $inf $out1 || exit 1
    local out2="${out}-zoom.png"
    wirecell-sigproc plot-response --region 2.5 --trange 55,85 $inf $out2 || exit 1
}


gar2wct $(resp indslc-colave)    0   1 0,1
gar2wct $(resp indave-colave)  0,1 0,1 0,1
gar2wct $(resp indave-colslc0) 0,1 0,1   0
gar2wct $(resp indave-colslc1) 0,1 0,1   1

plot $(resp indslc-colave)
plot $(resp indave-colave)
plot $(resp indave-colslc0)
plot $(resp indave-colslc1)

