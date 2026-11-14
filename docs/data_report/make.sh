#!/bin/sh
# Build Vietnamese (sh make.sh) or English (sh make.sh en).
# Uses fit_hcmus.sty and the logo from ../proposal/latex/.
cd "$(dirname "$0")" || exit 1
case "${1:-vi}" in
  vi) job=main; output=data_report.pdf ;;
  en) job=main_en; output=data_report_en.pdf ;;
  *) echo "Usage: sh make.sh [vi|en]"; exit 2 ;;
esac
build="build/$job"
mkdir -p "$build"
run() { xelatex -interaction=nonstopmode -halt-on-error -output-directory="$build" "$job.tex" > "$build/$1.txt" 2>&1; }
run run1 || { tail -30 "$build/$job.log"; exit 1; }
cp references.bib "$build/" || exit 1
(cd "$build" && bibtex "$job" > bib.txt 2>&1) || { cat "$build/bib.txt"; exit 1; }
run run2 || { tail -30 "$build/$job.log"; exit 1; }
run run3 || { tail -30 "$build/$job.log"; exit 1; }
if grep -E "There were undefined references|There were undefined citations|multiply defined" "$build/$job.log"; then
  exit 1
fi
cp "$build/$job.pdf" "$output" || exit 1
echo "Built $output"
