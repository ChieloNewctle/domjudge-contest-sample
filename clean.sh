#!/bin/bash

for i in z a; do
    echo $i
    (cd problems/$i && rm -f $i.zip problem.aux problem.log problem.pdf)
done
