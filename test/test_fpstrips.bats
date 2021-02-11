#!/usr/bin/env bats

datasets=("DV-1000V" "DV-2000V")

datadir () {
    echo "$(dirname $BATS_TEST_DIRNAME)/data/fpstrips"
}

datasetdir () {
    echo "$(datadir)/${1}"
}

datasetzipfile () {
    echo "$(datasetdir $1).zip"
}

download_dataset_from_dropbox () {
    local dataset="$1"; shift
    local url=""
    if [ "$dataset" = "DV-1000V" ] ; then
        url="https://www.dropbox.com/sh/tfbgqrebc94ia51/AAALKIJ7O2qcVAPOENYOjujba/DV-1000V?dl=0&subfolder_nav_tracking=1"
    elif [ "$dataset" = "DV-2000V" ] ; then
        url="https://www.dropbox.com/sh/tfbgqrebc94ia51/AAAxS_xfMUFzEVBXRZ_TVFt2a/DV-2000V?dl=0&subfolder_nav_tracking=1"
    else
        echo "# unknown dataset: $dataset" >&3
        exit 1
    fi

    mkdir -p "$(datadir)"
    local tgt="$(datasetzipfile $dataset)"
    if [ -f "$tgt" ] ; then
        echo "# Already have $tgt" >&3
        echo "$tgt"
        return
    fi
    wget --quiet -O "$tgt" "$url" >/dev/null
    echo "$tgt"
}
    

@test "download response calculation results from dropbox" {
    for ds in ${datasets[@]}
    do
        run download_dataset_from_dropbox "$ds"
        echo "$output"
        [ -n "$output" ] 
        [ "$output" = "$(datasetzipfile $ds)" ]
        [ -f "$output" ]
        [ -s "$output" ]
    done
}


unpack_response_calculations () {
    local dataset="$1"; shift
        
    local dsd="$(datasetdir $dataset)"
    if [ -d "$dsd" ] ; then
        echo "# Already have: $dsd" >&3
        echo "$dsd"
        return
    fi

    local dszf="$(datasetzipfile $dataset)"
    if [ ! -f "$dszf" ] ; then
        echo "# no dataset zip file: $dszf" >&3
        exit 1
    fi
    
    mkdir -p "$dsd"
    cd "$dsd"
    unzip "$dszf" > /dev/null
    echo "$dsd"
    cd -
}

@test "unpack response calcualtions" {
    for ds in ${datasets[@]}
    do
        echo $ds
        run unpack_response_calculations "$ds"
        echo "$output"
        [ -n "$output" ]
        [ -d "$output" ]
        [ -f "${output}/fort.151" ]
    done
}

repack_response_calculations () {
    local dataset="$1"; shift
        
    local dsd="$(datasetdir $dataset)"
    local tgt="${dsd}.tar.gz"

    if [ -f "$tgt" ] ; then
        echo "# Already have: $tgt" >&3
        echo "$tgt"
        return
    fi

    if [ ! -d "$dsd" ] ; then
        echo "# No dataset directory: $dsd" >&3
        exit -1
    fi
    if [ ! -f "$dsd/fort.151" ] ; then
        echo "# No representative file: $dsd/fort.151" >&3
        exit -1
    fi

    cd "$(datadir)"
    echo -n "# " >&3
    tar -czf "$tgt" "$dataset" >&3
    echo "$tgt"
    cd -    
}

@test "repack response calcualtions" {
    for ds in ${datasets[@]}
    do
        echo $ds
        run repack_response_calculations "$ds"
        echo "$output"
        [ -n "$output" ]
        [ -f "$output" ]
    done
}

