#!/bin/bash

source problems.sh

for i in $problems; do
    echo $i
    (cd problems/$i && rm -f $i.zip problem.aux problem.log problem.pdf)
done
