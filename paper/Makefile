# Build the manuscript for IEEE Transactions on Information Forensics and Security (IEEEtran).
#
#   make            -> main.pdf + supplement.pdf (IEEE TIFS: <= 10 pp / <= 6 pp)
#   make highlights -> highlights.pdf
#   make numbers    -> regenerate numbers.tex + figures from results/, then rebuild
#   make gate       -> submission gate; fails while any \PENDING remains
#   make check      -> gate + build hygiene (undefined refs, abstract length)
#   make clean      -> remove build artefacts (keeps main.pdf)
#   make cleanall   -> remove build artefacts and main.pdf

LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error
PY      = python3
ROOT    = ..

.PHONY: all highlights numbers legacy gate check package clean cleanall

all: main.pdf supplement.pdf

# main.tex and supplement.tex cross-reference each other through xr-hyper, so
# each is rebuilt after the other's .aux changes (latexmk -g forces the pass).
NUMBERS = numbers.tex numbers_postfix.tex numbers_postfix_p1.tex numbers_defect.tex numbers_defect_resnet.tex numbers_pilot.tex numbers_alias.tex numbers_calib6.tex numbers_falsify.tex numbers_r1.tex numbers_p3x.tex numbers_flameprobe.tex numbers_kgeom.tex numbers_k1.tex numbers_r2.tex

supplement.pdf: supplement.tex preamble.tex main.pdf $(NUMBERS)
	$(LATEXMK) supplement.tex
	$(LATEXMK) -g main.tex

main.pdf: main.tex preamble.tex refs.bib declarations_ieee.tex numbers.tex numbers_postfix.tex numbers_postfix_p1.tex numbers_defect.tex numbers_defect_resnet.tex numbers_pilot.tex numbers_alias.tex numbers_calib6.tex numbers_falsify.tex numbers_r1.tex numbers_p3x.tex numbers_flameprobe.tex numbers_kgeom.tex numbers_k1.tex numbers_r2.tex $(wildcard figs/*)
	$(LATEXMK) main.tex

highlights: highlights.tex
	$(LATEXMK) highlights.tex

# Regenerate every number and figure from the committed result files, then
# rebuild. Run this after each lane of run_remediation.sh completes.
#
# Iteration 15: the legacy steps (aggregate_multiseed.py, experiments.make_tables,
# make_figs.py) belong to the pre-fix campaign voided in iteration 1 (its JSONs are
# archived in results/_pre_counterfix and no longer produce results/summary.csv).
# None of their outputs is used by main.tex or supplement.tex (the only figure is
# fig_p1_geometry.pdf; the only numbers.tex macros used are the realizability \rz*
# ones, which make_numbers.py reads from results/realizability_ciciot2023.json).
# aggregate_multiseed.py would also pool the calibration campaigns (calib_iter*)
# into summary_multiseed.csv as if they were a headline campaign, so it is NOT run
# here; make_numbers.py then marks those unused macros \PENDING. Kept as `legacy`.
numbers:
	cd $(ROOT) && $(PY) paper/make_numbers.py
	# P3 is the campaign of record (iteration 10); the stopped P1/P2 campaign is kept
	# as \pa... macros in numbers_postfix_p1.tex (defective round-one engine).
	cd $(ROOT) && $(PY) paper/analyse_postfix.py --res results/postfix_p3 --atk-res results/postfix_p3 --target 1040 --prereg iterations/PREREG_P3.md
	cd $(ROOT) && $(PY) paper/analyse_postfix.py --res results/postfix_p1 --atk-res results/postfix_p2 --prefix pa --out paper/numbers_postfix_p1.tex --implant-bsr 0
	cd $(ROOT) && $(PY) paper/make_numbers_pilot.py
	cd $(ROOT) && $(PY) paper/make_numbers_alias.py
	cd $(ROOT) && $(PY) paper/make_numbers_calib6.py
	cd $(ROOT) && CUDA_VISIBLE_DEVICES= $(PY) experiments/counter_defect/fltrust_falsify.py
	cd $(ROOT) && $(PY) paper/make_fig_p1.py --res results/postfix_p3
	cd $(ROOT) && $(PY) paper/make_numbers_generality.py
	cd $(ROOT) && $(PY) paper/make_numbers_fltshut.py
	# P3X (iterations/PREREG_P3X.md): held-out replication of P3's exploratory detection effects
	cd $(ROOT) && $(PY) paper/analyse_p3x.py
	# FLAME mechanism probe (iteration 29; experiments/flame_probe/flame_probe.py, logging only)
	cd $(ROOT) && $(PY) paper/make_numbers_flameprobe.py
	# Counter-angle identity checks (iteration 30; Proposition prop:angle)
	cd $(ROOT) && $(PY) paper/make_numbers_kgeom.py
	# K1 (iterations/PREREG_K1.md): registered k>1 reversal test of Proposition prop:angle
	cd $(ROOT) && $(PY) paper/analyse_k1.py
	# R1 (iterations/PREREG_R1.md): trained counter-falsifying attacker; paper/numbers_r1.tex
	cd $(ROOT) && $(PY) paper/analyse_r1.py
	# R2 (iterations/PREREG_R2.md): byzantineFL re-run with/without the mask; paper/numbers_r2.tex
	cd $(ROOT) && $(PY) paper/analyse_r2.py
	$(LATEXMK) main.tex
	$(LATEXMK) supplement.tex
	$(LATEXMK) -g main.tex

# Pre-fix campaign figures/tables (void since iteration 1; needs results/summary.csv,
# which only exists if the archived JSONs are restored). Not part of the paper.
legacy:
	cd $(ROOT) && $(PY) paper/aggregate_multiseed.py
	cd $(ROOT) && $(PY) -m experiments.make_tables
	cd $(ROOT) && $(PY) paper/make_figs.py

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
