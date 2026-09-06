#!/usr/bin/env bash
# Assemble a flat submission directory for Editorial Manager.
#
# Elsevier's LaTeX instructions are explicit: "All submission files -- including
# figures, tables, and style and bibliographic files -- must be stored at the
# same folder level." Subfolders are not allowed. This repository keeps figures
# in figs/ for sanity, so the submission copy is flattened here rather than the
# working tree being made awkward.
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
cp main.tex numbers.tex declarations.tex refs.bib main.bbl "$OUT"/

# Figure item type, flattened out of figs/.
cp figs/*.pdf "$OUT"/

# Uploaded separately at submission, not part of the manuscript item.
cp highlights.tex highlights.pdf main.pdf "$OUT"/

# Not uploaded; carried so the folder is self-describing.
cp README.txt cover_letter.md "$OUT"/

echo "Flat submission folder: $(pwd)/$OUT"
echo
echo "Verifying it builds standalone..."
( cd "$OUT" && latexmk -pdf -interaction=nonstopmode main.tex >/dev/null 2>&1 \
  && echo "  build OK: $(pdfinfo main.pdf | awk '/Pages/{print $2}') pages" \
  || { echo "  BUILD FAILED in the flat copy"; exit 1; } )

( cd "$OUT" && latexmk -c >/dev/null 2>&1 || true )

echo
echo "Upload to Editorial Manager as:"
echo "  Manuscript : main.tex numbers.tex declarations.tex refs.bib main.bbl"
echo "  Figure     : $(ls "$OUT"/fig_*.pdf | wc -l) x fig_*.pdf"
echo "  Highlights : highlights.tex (and highlights.pdf)"
echo "  PDF proof  : main.pdf"
echo
echo "Do NOT upload LaTeX files as Supplemental items."
