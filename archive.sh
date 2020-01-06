#!/bin/bash

source problems.sh

for i in $problems; do
    dest=$zip_prefix-$i.zip
    echo $i
    (cd problems/$i \
        && rm -f $dest && zip -r $dest $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
        && mv $dest .. \
    )
done
