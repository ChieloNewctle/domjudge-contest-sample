#!/bin/bash

zip_prefix=c1-

source problems.sh

for i in $problems; do
    echo $i
    dest=$zip_prefix$1.zip
    (cd problems/$i \
        && rm -f $dest && zip -r $dest $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
    )
done
