#!/usr/bin/env python3
"""Pre-submission hygiene checks for the JISA manuscript.

Run from paper/ (or via `make check`). Exits non-zero on any failure, so it
can gate a commit. These are the checks that a build alone does not catch:
JISA's 250-word abstract cap, Elsevier's 85-character Highlights cap, and the
citation/reference regressions that hide in a clean-looking build.
"""
import re
import sys

FAILURES = []


def check(ok, label, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}{('  -- ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)


def strip_tex(s):
    s = re.sub(r'%.*', '', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?', ' ', s)
    return re.sub(r'[{}$~\\]', ' ', s)


def main():
    tex = open('main.tex', encoding='utf-8').read()

    # JISA: abstract must not exceed 250 words.
    m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.S)
    words = len(strip_tex(m.group(1)).split()) if m else -1
    check(0 < words <= 250, "abstract <= 250 words", f"{words} words")

    # Elsevier: each highlight <= 85 characters including spaces.
    try:
        hl = [l.strip()[6:].replace(r'\%', '%').strip()
              for l in open('highlights.tex', encoding='utf-8')
              if l.strip().startswith(r'\item')]
        over = [h for h in hl if len(h) > 85]
        check(3 <= len(hl) <= 5, "highlights: 3-5 bullets", f"{len(hl)} bullets")
        check(not over, "highlights <= 85 chars each",
              f"{len(over)} over" if over else "")
    except FileNotFoundError:
        check(False, "highlights.tex present")

    # Build hygiene.
    try:
        log = open('main.log', encoding='utf-8', errors='replace').read()
    except FileNotFoundError:
        check(False, "main.log present (build first)")
        return 1
    for label, pat in [("no undefined citations", r'Citation .* undefined'),
                       ("no undefined references", r'Reference .* undefined'),
                       ("no undefined control sequences", r'Undefined control sequence'),
                       ("no missing-character warnings", r'Missing character')]:
        hits = len(re.findall(pat, log))
        check(hits == 0, label, f"{hits} found" if hits else "")

    # Every float must be referred to in the text. An orphaned table or figure
    # is something a copy-editor will send back, and it is easy to create by
    # deleting the one sentence that pointed at it.
    labels = set(re.findall(r'\\label\{((?:tab|fig):[^}]+)\}', tex))
    refs = set(re.findall(r'\\ref\{((?:tab|fig):[^}]+)\}', tex))
    orphans = sorted(labels - refs)
    check(not orphans, "every table and figure is cross-referenced",
          ", ".join(orphans) if orphans else "")

    # Sec. 6 claims every number in the paper is a generated macro. It was not
    # true when written -- 28 distinct decimals were hand-typed in the prose, and
    # two of them were factually wrong (the grid BSR floor, and FLNET's macro-F1).
    # Guard the claim: any literal decimal in prose or a caption that is not on
    # the allowlist below is a number that should be coming from the generator.
    ALLOWED = {
        # experiment parameters and thresholds, not measurements
        '0.0', '0.1', '0.2', '0.3', '0.05', '0.25', '0.5', '1.0', '1.5', '2.0',
        '3.0', '0.02',
        # ResNet-18 probe optimiser (SGD learning rate, momentum)
        '0.01', '0.9',
        # (iteration 3: the evasion, FLNET and donor-screen literals left the paper
        # with the superseded body; their allowlist entries are removed so any
        # reappearance fails this check.)
    }
    prose = re.sub(r'\\begin\{tabular\}.*?\\end\{tabular\}', '',
                   tex[tex.index(r'\begin{document}'):], flags=re.S)
    prose = re.sub(r'(?m)^\s*%.*$', '', prose)
    stray = set()
    for m in re.finditer(r'\$([^$]*?)\$', prose):
        if re.search(r'\\[A-Za-z]+', m.group(1)):
            continue
        for num in re.findall(r'(?<![\d.])\d*\.\d+(?![\d])', m.group(1)):
            if num not in ALLOWED:
                stray.add(num)
    check(not stray, "no unexplained hand-entered numbers in prose",
          ", ".join(sorted(stray)) if stray else
          f"{len(ALLOWED)} known literals allowlisted")

    # The abstract and the introduction both state that the evasion drives the
    # colluders' mean pairwise cosine "below 0.35". That figure came from a
    # reduced-scale validation run (6 clients, 3 rounds, 8k rows) -- the body
    # says so and marks it \PENDING -- but the abstract states it flat. As the
    # full-scale lane 1a cells land, adMalCos*{Decorrelated,Adaptive} resolve
    # with the real numbers. Compare them against the claim, so a headline
    # figure cannot go stale silently. This is exactly the class of error the
    # generator exists to stop, and the abstract is the one place it can still
    # hide, because that sentence is not itself a macro.
    nums = open('numbers.tex', encoding='utf-8').read()
    measured = [(d, v, float(x)) for d, v, x in re.findall(
        r'\\newcommand\{\\adMalCos(\w+?)(Decorrelated|Adaptive)\}\{([0-9.]+)\}', nums)]
    claim = re.search(r'to below \$0\.(\d+)\$', tex)
    if measured and claim:
        bound = float('0.' + claim.group(1))
        worst = max(x for _, _, x in measured)
        ok = worst < bound
        check(ok, f"abstract's collusion-cosine claim (below {bound}) holds at full scale",
              f"worst measured {worst:.3f} over {len(measured)} cell(s)"
              + ("" if ok else "  <-- ABSTRACT AND INTRO OVERSTATE THE EVASION"))
        if not ok:
            # FedAvg is the undefended baseline. The abstract's sentence is
            # unqualified, but if the claim holds across every rule that
            # actually reads direction, restricting it is an honest fix and
            # cheaper than weakening the number. Report both so the choice is
            # made on the evidence rather than on convenience.
            defended = [x for d, _, x in measured if d != 'fedavg']
            print("        measured, by defense and variant:")
            for d, v, x in sorted(measured, key=lambda t: -t[2]):
                print(f"          {x:.3f}  {d} / {v.lower()}"
                      + ("   (undefended baseline)" if d == 'fedavg' else ""))
            if defended:
                print(f"        excluding FedAvg: worst {max(defended):.3f} over "
                      f"{len(defended)} cell(s) -> claim "
                      f"{'HOLDS' if max(defended) < bound else 'still fails'}")
            else:
                print("        no defended cells yet -- verdict is on the "
                      "undefended baseline alone, which is weak evidence")
    elif claim:
        print(f"SKIP  abstract's collusion-cosine claim (below "
              f"{float('0.' + claim.group(1))}) -- no full-scale cells yet")

    # The submission gate. Counted from source, not from the PDF: a marker that
    # wraps across a narrow table cell reaches pdftotext as two lines, so a text
    # search of the PDF undercounts. Every reference in the body to a macro that
    # numbers.tex leaves unresolved is one marker, plus every literal \PENDING
    # hedge in the prose and captions.
    pend_macros = set()
    for nf in ('numbers.tex', 'numbers_postfix.tex', 'numbers_defect.tex',
               'numbers_defect_resnet.tex', 'numbers_pilot.tex'):
        try:
            pend_macros |= set(re.findall(
                r'\\(?:newcommand|providecommand)\{\\([A-Za-z]+)\}\{\\PENDING',
                open(nf, encoding='utf-8').read()))
        except FileNotFoundError:
            check(False, f"{nf} present (run its generator)")
    body = tex[tex.index(r'\begin{document}'):]
    body = re.sub(r'(?m)^\s*%.*$', '', body)
    refs = [m for m in re.findall(r'\\([A-Za-z]+)', body) if m in pend_macros]
    literal = len(re.findall(r'\\PENDING(?![A-Za-z])', body))
    fam = {}
    for r in refs:
        k = re.match(r'[a-z]+', r).group()
        fam[k] = fam.get(k, 0) + 1
    total = len(refs) + literal
    detail = f"{total} = {len(refs)} macro refs {fam} + {literal} literal"
    check(total == 0, "no unresolved results in the manuscript", detail if total else "")

    if total:
        # Each literal hedge carries a "% RETIRES WITH:" annotation naming the
        # lane of run_remediation.sh that resolves it. Report the outstanding
        # work grouped by lane, so the gate says what to run rather than only
        # that it failed.
        lanes = {}
        for lane in re.findall(r'% RETIRES WITH: (.+)', tex):
            lanes[lane] = lanes.get(lane, 0) + 1
        macro_lane = {'ad': 'lane 1a, adaptive-vs-direction',
                      'ev': 'lane 1b, evasion-noise-sweep',
                      'res': 'lane 1c, adaptive-vs-residual',
                      'mg': 'lane 3, magnitude-based-defenses',
                      'dn': 'lane 4, donor-triggers',
                      'ms': 'lanes 5a-5c, seeds',
                      'ni': 'lane 6, non-IID breadth',
                      'rat': 'lane 5c, ratio-sweep-seeds',
                      'fl': 'FLNET lanes',
                      'pf': 'P1 paired A/B (experiments/postfix/run_p1.sh)'}
        for k, v in sorted(fam.items(), key=lambda kv: -kv[1]):
            lanes[macro_lane.get(k, k)] = lanes.get(macro_lane.get(k, k), 0) + v
        print("\n      outstanding by lane:")
        for lane, n in sorted(lanes.items(), key=lambda kv: -kv[1]):
            print(f"        {n:3d}  {lane}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: " + ", ".join(FAILURES))
        return 1
    print("all checks passed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
