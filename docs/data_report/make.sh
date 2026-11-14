#!/bin/sh
# Build build/main.pdf (XeLaTeX + BibTeX). Run from Git Bash: sh make.sh
# Uses fit_hcmus.sty and the logo from ../proposal/latex/.
cd "$(dirname "$0")" || exit 1
mkdir -p build
run() { xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > "build/$1.txt" 2>&1; }
run run1 || { grep -A5 "^!" build/main.log | head -20; exit 1; }
(cp references.bib build/ && cd build && bibtex main > bib.txt 2>&1; grep -iE "error|warning" bib.txt)
run run2
run run3 || { grep -A5 "^!" build/main.log | head; exit 1; }
grep -cE "undefined|multiply defined" build/main.log
cp build/main.pdf data_report.pdf
