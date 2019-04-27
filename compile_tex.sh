#!/bin/bash

for i in z a; do # first compile the tex file that imports all the problems
    echo $i
    (cd problems/$i \
        && xelatex problem.tex \
        && xelatex problem.tex && rm -f problem.aux \
    )
    # rerun xelatex to set LastPage correctly
done
