#!/bin/bash

# This assists in generating content for the TDR.  It relies on
# dune-reqs from dune-params project in DUNE's GitHub.  Most people
# don't have to mess with this.

dunegen-untar () {
    tf="$1"; shift
    if [ -z "$tf" ] ; then exit; fi

    tdir=$(mktemp -d "/tmp/dunegen-$(basename $tf .tar)-XXXXX")
    tar -C $tdir -xf $tf
    for one in $tdir/*.xlsx
    do
        # take first
        echo "$one"
        return
    done
    # here if fail
    rm -rf $tdir
}

dunegen-reqs () {
    ccode="$1" ; shift
    docid=$1 ; shift
    templ=$1 ; shift
    out=$1; shift
    if [ ! -f "$docid" ] ; then
        exit -1
    fi
    tf="$(dirname $docid)/$(cat $docid).tar"
    xlsf=$(dunegen-untar $tf)

    set -x
    
    dune-reqs render -C "$ccode" -t "$templ" -o $out $xlsf || exit 1

    tdir=$(dirname $xlsf)
    if [ -d "$tdir" ] ; then
        rm -rf "$tdir"
    fi

    set +x
}
dunegen-reqs-one-and-all () {
    ccode="$1" ; shift

    docid="$1" ; shift
    onetempl="$1" ; shift
    alltempl="$1" ; shift

    oneout="$1"; shift
    allout="$1"; shift
    oneout="$(dirname $allout)/$oneout" # make sure target correct directory

    if [ ! -f "$docid" ] ; then
        exit -1
    fi
    tf="$(dirname $docid)/$(cat $docid).tar"
    xlsf="$(dunegen-untar $tf)"
    # use default '-c collection' option.
    set -x

    dune-reqs render-one -C "$ccode" -t "$onetempl" -T "$alltempl" -o "$oneout" -O "$allout" "$xlsf" || exit 1
    set +x
}

dunegen-render-specs () {
    ccode="$1" ; shift
    xlsfile="$(readlink -f $1)"; shift

    origdir=$(pwd)
    mydir=$(dirname $(readlink -f $BASH_SOURCE))
    topdir=$(dirname $mydir)
    blddir="$topdir/build"
    cd $blddir
    dune-reqs render-one -C $ccode -t "../util/templates/spec-table-one.tex.j2" -T "../util/templates/spec-table-all.tex.j2" -o "../generated/req-${ccode}-{label}.tex" -O "../generated/req-${ccode}-all.tex" "$xlsfile"
    cd $origdir

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
