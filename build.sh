#!/bin/bash

for i in z a; do # first compile the tex file that imports all the problems
	echo $i
	(cd problems/$i \
        && xelatex problem.tex \
        && xelatex problem.tex && rm -f problem.aux \
        && rm -f $i.zip && zip -r $i.zip $(realpath --relative-to=$PWD \
            $(readlink -e problem.pdf problem.yaml domjudge-problem.ini data submissions)) \
    )
    # rerun xelatex to correct LastPage definition
done
