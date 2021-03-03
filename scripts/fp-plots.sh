#!/bin/bash
if [ -z "$1" ] ; then

    for res in 3D 2D MB
    do
        $0 $res
    done
    exit 0
fi

res="$1" ; shift

if [ "$res" = 3D ] ; then
    resfile=dv-2000v.json.bz2
    title="3D->2D"
    trange="80,120"
elif [ "$res" = "MB" ] ; then
    resfile=$HOME/dev/wct/data/ub-10-wnormed.json.bz2
    title="MB"
    trange="50,90"
else
    resfile=pcbro-response-avg.json.bz2
    title="2.5D"
    trange="40,80"
fi

wirecell-sigproc \
    plot-response \
    --title "$title" --region 0 --trange "$trange" --reflect \
    "$resfile" "resp-${res}-full.png"

wirecell-sigproc \
    plot-response-conductors \
    --log10 --title "$title" --trange "$trange" \
    "$resfile" "resp-${res}-wfs-lg10.png"

wirecell-sigproc \
    plot-response-conductors \
    --title "$title" --trange "$trange" \
    "$resfile" "resp-${res}-wfs.png"


