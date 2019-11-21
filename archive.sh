#!/bin/bash

source problems.sh

for i in $problems; do
    echo $i
    (cd problems/$i \
        && rm -f $i.zip && zip -r $i.zip $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
    )
done
