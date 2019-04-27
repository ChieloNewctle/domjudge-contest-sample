#!/bin/bash

./compile_tex.sh

for i in z a;
    echo $i
    (cd problems/$i \
        && rm -f $i.zip && zip -r $i.zip $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
    )
done
