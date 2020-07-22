#!/bin/bash

## made from select files from Yichen's Garfield output
# tar -cvf garfield-pcb.tar \
#   pcb_try/*_ind_*.dat \
#   pcb_try_add/{0.2,0.3,0.7,0.8,1.2,1.3,1.7}_col_*.dat \
#   pcb_try/{0.0,0.5,1.0,1.5}_col_*.dat
garfield_tarfile=${1:-$HOME/work/pcbro/fields/garfield-pcb.tar}

resp () {
    echo "pcbro-response-${1}.json.bz2"
}

gar2wct () {
    local out=$1 ; shift
    local u=$1 ; shift
    local v=$1 ; shift
    local w=$1 ; shift
    if [ -f $out ] ; then
        echo "file exists: $out"
        return
    fi
    echo "generating: $out"
    wirecell-pcbro convert-garfield -U $u -V $v -W $w $garfield_tarfile $out
}

plot () {
    local inf=$1 ; shift
    local out=$(basename $inf .json.bz2)

    local out1="${out}.png"
    wirecell-sigproc plot-response --region 2.5 --trange  0,85 $inf $out1
    local out2="${out}-zoom.png"
    wirecell-sigproc plot-response --region 2.5 --trange 55,85 $inf $out2
}


gar2wct $(resp impslc-colave)    0   1 0,1
gar2wct $(resp impave-colave)  0,1 0,1 0,1
gar2wct $(resp impave-colslc0) 0,1 0,1   0
gar2wct $(resp impave-colslc1) 0,1 0,1   1

plot $(resp impslc-colave)
plot $(resp impave-colave)
plot $(resp impave-colslc0)
plot $(resp impave-colslc1)

