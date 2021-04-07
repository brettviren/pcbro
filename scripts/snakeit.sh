#!/bin/bash

sdir="$(dirname $(realpath $BASH_SOURCE))"
srcdir="$(dirname $sdir)"

cd "$srcdir"

snakemake -jall --configfile=$sdir/snakeit-$USER.json $@
