#!/bin/bash

source vars.sh

generated="problem_statement/wrap.aux problem_statement/wrap.log problem_statement/wrap.pdf problem.pdf"

if [ $# -ne 0 ]; then
    problems=$*
fi

for i in $problems; do
    echo $i
    (cd problems/$i && rm -f $prefix-$i.zip $generated)
done
