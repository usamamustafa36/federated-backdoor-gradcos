#!/usr/bin/env bash
# Assemble a flat submission directory. This repository keeps figures in figs/,
# so the submission copy is flattened here.
#
# main.tex needs no edit: \graphicspath{{figs/}} only *adds* a search path, and
# LaTeX still finds the flattened figures in the current directory.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."

OUT=submission
rm -rf "$OUT"
mkdir -p "$OUT"

# Manuscript item type: .tex, .bbl, .bib. numbers.tex and declarations.tex are
# \input by main.tex, so they must travel with it.
cp main.tex preamble.tex supplement.tex numbers*.tex declarations_ieee.tex refs.bib main.bbl "$OUT"/   # iteration 12: shared preamble, all generated numbers files, supplement

# Figure item type, flattened out of figs/.
cp figs/*.pdf "$OUT"/

# Compiled manuscript and supplement.
cp main.pdf supplement.pdf "$OUT"/

# Not uploaded; carried so the folder is self-describing.
cp README.txt "$OUT"/

echo "Flat submission folder: $(pwd)/$OUT"
echo
echo "Verifying it builds standalone..."
( cd "$OUT" && latexmk -pdf -interaction=nonstopmode main.tex >/dev/null 2>&1 \
  && echo "  build OK: $(pdfinfo main.pdf | awk '/Pages/{print $2}') pages" \
  || { echo "  BUILD FAILED in the flat copy"; exit 1; } )

( cd "$OUT" && latexmk -c >/dev/null 2>&1 || true )

echo
echo "Upload: main.tex supplement.tex preamble.tex numbers*.tex declarations_ieee.tex refs.bib main.bbl, $(ls "$OUT"/fig_*.pdf | wc -l) figures, main.pdf, supplement.pdf"
