#!/bin/sh
# Build build/main.pdf (XeLaTeX + BibTeX). Run: sh make.sh
cd "$(dirname "$0")" || exit 1
mkdir -p build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/run1.txt 2>&1 || { grep -A5 "^!" build/main.log | head -20; exit 1; }
(cp references.bib build/ && cd build && bibtex main > bib.txt 2>&1; grep -iE "error|warning" bib.txt)
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/run2.txt 2>&1
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/run3.txt 2>&1 || { grep -A5 "^!" build/main.log | head; exit 1; }
pdfinfo build/main.pdf | grep Pages
