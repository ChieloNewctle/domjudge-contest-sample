#!/bin/bash

source vars.sh

compile_tex() {
    (cd problems/$1/problem_statement \
        && xelatex wrap.tex \
        && xelatex wrap.tex \
        && xelatex wrap.tex && rm -f wrap.aux \
        && cp wrap.pdf ../problem.pdf \
    )
}

if [ $# -ne 0 ]; then
    problems=$*
fi

for i in $problems; do # first compile the tex file that imports all the problems
    echo $i
    compile_tex $i
    # rerun xelatex to set LastPage correctly
done
