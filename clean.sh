#!/bin/bash

source problems.sh

for i in $problems; do
    echo $i
    dest=$zip_prefix-$i.zip
    (cd problems/$i && rm -f ../$dest problem.aux problem.log problem.pdf)
done
