#!/bin/bash

source vars.sh

archive() {
    (cd problems/$1 \
        && rm -f $prefix-$1.zip \
        && zip -r $prefix-$1.zip $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
    )
}

if [ $# -ne 0 ]; then
    problems=$*
fi

for i in $problems; do
    echo $i
    archive $i
done
