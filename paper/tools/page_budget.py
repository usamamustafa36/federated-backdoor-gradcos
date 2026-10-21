#!/usr/bin/env python3
"""Measure how many IEEEtran pages each section, paragraph and float of a paper uses.

Iteration 12. Copies paper/ to a temporary directory, inserts zero-height
\\pdfsavepos markers (whatsits in vertical mode: they do not change the layout,
which the script verifies by comparing pdftotext output with an unmarked build)
before every \\section, \\subsection, bold paragraph head and theorem-like
environment, and at the top and bottom of every float. Positions are converted
to "page units" (one page = two columns of \\textheight).

Text per block = column span between consecutive markers minus the float area
that physically lies inside that span. Floats are attributed to the block in
whose source they appear (their size in pages: table*/figure* = height/textheight,
single-column = half that). An allowance of 14 pt per float stands in for the
float separation.

    python3 paper/tools/page_budget.py [main.tex]
"""
import json, os, re, shutil, subprocess, sys, tempfile

SP = 65536.0


def build(d, stem):
    for cmd in (['pdflatex', '-interaction=nonstopmode', stem + '.tex'],
                ['bibtex', stem],
                ['pdflatex', '-interaction=nonstopmode', stem + '.tex'],
                ['pdflatex', '-interaction=nonstopmode', stem + '.tex']):
        subprocess.run(cmd, cwd=d, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    src_name = sys.argv[1] if len(sys.argv) > 1 else 'main.tex'
    paper = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = tempfile.mkdtemp(prefix='budget_')
    for f in os.listdir(paper):
        p = os.path.join(paper, f)
        if f.endswith(('.tex', '.bib', '.bst', '.cls', '.aux')) or f == 'figs':
            (shutil.copytree if os.path.isdir(p) else shutil.copy)(p, os.path.join(tmp, f))
    L = open(os.path.join(tmp, src_name), encoding='utf-8').read().split('\n')
    out, names, inf, k, f, prev = [], {}, 0, 0, 0, ''
    for l in L:
        mb = re.match(r'\s*\\begin\{(table\*?|figure\*?)\}', l)
        me = re.match(r'\s*\\end\{(table\*?|figure\*?)\}', l)
        if mb:
            inf += 1; f += 1; names['f%d' % f] = mb.group(1)
            out += [l, '\\mk{ft%d}' % f]; prev = l; continue
        if me:
            inf -= 1; out += ['\\mk{fb%d}' % f, l]; prev = l; continue
        head = re.match(r'\s*\\(section|subsection)\*?\{', l)
        para = (not inf and prev.strip() == '' and
                re.match(r'(\\textbf\{|\\paragraph\{|\\begin\{(proposition|corollary|lemma|theorem)\})', l))
        if head or para or l.startswith('\\bibliography{'):
            k += 1; names['m%d' % k] = l.strip()[:64]; out.append('\\mk{m%d}' % k)
        if l.startswith('\\end{document}'):
            out.append('\\mk{mend}')
        out.append(l); prev = l
    t = '\n'.join(out)
    defs = ('\\makeatletter\\def\\mkpos#1#2#3#4{}\\def\\mk#1{\\pdfsavepos\\write\\@auxout'
            '{\\string\\mkpos{#1}{\\the\\pdflastxpos}{\\the\\pdflastypos}{\\thepage}}}\\makeatother\n')
    geom = ('\\typeout{GEOM \\the\\topmargin\\space\\the\\headheight\\space\\the\\headsep'
            '\\space\\the\\textheight\\space\\the\\paperheight\\space\\the\\oddsidemargin'
            '\\space\\the\\columnwidth\\space\\the\\columnsep}')
    t = t.replace('\\begin{document}', defs + '\\begin{document}' + geom, 1)
    open(os.path.join(tmp, 'mk.tex'), 'w', encoding='utf-8').write(t)
    base = t.replace(defs, defs.replace('\\pdfsavepos\\write', '\\gobblemk\\write')
                     ).replace('\\makeatletter\\def\\mkpos', '\\makeatletter\\def\\gobblemk\\write#1#2{}\\def\\mkpos', 1)
    open(os.path.join(tmp, 'base.tex'), 'w', encoding='utf-8').write(base)
    build(tmp, 'mk'); build(tmp, 'base')
    txt = lambda s: subprocess.run(['pdftotext', os.path.join(tmp, s + '.pdf'), '-'],
                                   capture_output=True, text=True).stdout
    same = txt('mk') == txt('base')
    log = open(os.path.join(tmp, 'mk.log'), encoding='utf-8', errors='replace').read()
    g = [float(x[:-2]) for x in re.search(r'GEOM (.*)', log).group(1).split()]
    top, hh, hs, H, ph, osm, cw, cs = g
    YT = ph - (72 + top + hh + hs)
    xsplit = 72 + osm + cw + cs / 2
    pos = {m[0]: (int(m[1]) / SP, int(m[2]) / SP, int(m[3]))
           for m in re.findall(r'\\mkpos\{(\w+)\}\{(\d+)\}\{(\d+)\}\{(\d+)\}',
                               open(os.path.join(tmp, 'mk.aux')).read())}

    def u(n):
        x, y, p = pos[n]
        return 2 * (p - 1) + (0 if x < xsplit else 1) + (YT - y) / H

    order = re.findall(r'\\mk\{(\w+)\}', t)
    floats, own, cur = [], {}, None
    for n in order:
        if n[0] == 'm':
            cur = n
        if n.startswith('ft'):
            i = n[2:]; own[i] = cur
            (xt, yt, p), (xb, yb, pb) = pos['ft' + i], pos['fb' + i]
            star = names['f' + i].endswith('*')
            cols = [2 * (p - 1), 2 * (p - 1) + 1] if star else [2 * (p - 1) + (0 if xt < xsplit else 1)]
            floats.append(dict(id=i, kind=names['f' + i], h=yt - yb + 14, cols=cols, top=(YT - yt) / H))
    blocks = [n for n in order if n[0] == 'm' and n in pos]
    print(f'{"block":<66} {"text":>5} {"float":>5}')
    tt = tf = 0
    for a, b in zip(blocks, blocks[1:]):
        ua, ub = u(a), u(b)
        sub = sum(max(0, min(ub, c + fl['top'] - .02 + fl['h'] / H) - max(ua, c + fl['top'] - .02))
                  for fl in floats for c in fl['cols'])
        mine = [fl for fl in floats if own[fl['id']] == a]
        fp = sum(fl['h'] / H * len(fl['cols']) / 2 for fl in mine)
        text = (ub - ua - sub) / 2
        tt += text; tf += fp
        tag = ' '.join('%s(%.2f)' % (fl['kind'], fl['h'] / H * len(fl['cols']) / 2) for fl in mine)
        indent = '' if re.match(r'\\(section|bibliography)', names.get(a, '')) else '  '
        print(f'{indent + names.get(a, a):<66} {text:5.2f} {fp:5.2f} {tag}')
    print(f'front matter (title/abstract) {u(blocks[0]) / 2:.2f}; text {tt:.2f}; floats {tf:.2f}; '
          f'end of document at {u(blocks[-1]) / 2:.2f} pages')
    print('layout identical to an unmarked build: %s' % ('yes' if same else 'NO (numbers approximate)'))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
