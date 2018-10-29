#!/bin/bash

# This assists in generating content for the TDR.  It relies on
# dune-reqs from dune-params project in DUNE's GitHub.  Most people
# don't have to mess with this.

dunegen-untar () {
    tf="$1"; shift
    if [ -z "$tf" ] ; then exit; fi

    tdir=$(mktemp -d '/tmp/dunegen-XXXXX')
    for one in $(tar -C $tdir -xvf $tf)
    do
        if [[ $one =~ ^.*\.xlsx$ ]] ; then
            echo "$tdir/$one"
            return
        fi
    done
    rm -rf $tdir
}

dunegen-reqs () {
    docid=$1 ; shift
    templ=$1 ; shift
    out=$1; shift
    if [ ! -f "$docid" ] ; then
        exit -1
    fi
    tf="$(dirname $docid)/$(cat $docid).tar"
    xlsf=$(dunegen-untar $tf)
    dune-reqs render -t $templ -o $out $xlsf
}


dunegen-help () {
    cat <<EOF
usage: $0 <cmd> [cmd options]
EOF
}
dunegen- () {
    dunegen-help
}


cmd=$1 ; shift
dunegen-$cmd $@
