# Build the manuscript for the Journal of Information Security and Applications.
#
#   make            -> main.pdf
#   make highlights -> highlights.pdf
#   make numbers    -> regenerate numbers.tex + figures from results/, then rebuild
#   make gate       -> submission gate; fails while any \PENDING remains
#   make check      -> gate + build hygiene (undefined refs, abstract length)
#   make clean      -> remove build artefacts (keeps main.pdf)
#   make cleanall   -> remove build artefacts and main.pdf

LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error
PY      = python3
ROOT    = ..

.PHONY: all highlights numbers gate check package clean cleanall

all: main.pdf

main.pdf: main.tex refs.bib declarations.tex numbers.tex numbers_postfix.tex numbers_defect.tex $(wildcard figs/*)
	$(LATEXMK) main.tex

highlights: highlights.tex
	$(LATEXMK) highlights.tex

# Regenerate every number and figure from the committed result files, then
# rebuild. Run this after each lane of run_remediation.sh completes.
numbers:
	cd $(ROOT) && $(PY) paper/aggregate_multiseed.py
	cd $(ROOT) && $(PY) -m experiments.make_tables
	cd $(ROOT) && $(PY) paper/make_numbers.py
	cd $(ROOT) && $(PY) paper/make_figs.py
	$(LATEXMK) main.tex

# The submission gate. Nothing carrying a \PENDING may go to a venue.
gate:
	cd $(ROOT) && $(PY) paper/make_numbers.py --strict

check: gate
	@$(PY) tools/check_manuscript.py

# Flat folder for Editorial Manager -- Elsevier forbids subfolders in a
# submission. Verifies the flattened copy still builds.
package: main.pdf highlights
	@bash tools/make_package.sh

clean:
	latexmk -c
	rm -f *.bbl *.spl
	rm -rf submission

cleanall:
	latexmk -C
	rm -f *.bbl *.spl
