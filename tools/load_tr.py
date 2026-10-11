# -*- coding: utf-8 -*-
r"""하스피 번역 받기(2026-10-11) — my files/번역/QV2_{음성자막,브리핑막간,메뉴그림}_NN[_ko|_번역].tsv
  ★번역자가 셀 안에 «날 줄바꿈»을 친 경우가 있다(브리핑막간_02) → id 열 모양으로 «새 행 시작»을 판정해 이어 붙이고 \n 으로 바꿈.
  load(kind) → {id: 번역}, 원본 id 목록과 대조.
  python tools/load_tr.py   → 통계·누락·용어 변형 보고
"""
import collections, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'my files', '번역')
IDPAT = {'음성자막': re.compile(r'^WD[0-9A-Z]{3}/V[0-9A-F]{4}#\d+_\d+\t'),
         '브리핑막간': re.compile(r'^[FL][0-9A-F]{3}\t'),
         '메뉴그림': re.compile(r'^[A-Z_0-9]+_\d\d\t')}
TCOL = {'음성자막': 7, '브리핑막간': 5, '메뉴그림': 4}


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(SRC, 'QV2_%s_*.tsv' % kind))):
        txt = open(p, encoding='utf-8-sig').read().replace('\r\n', '\n')
        lines = txt.split('\n')[1:]
        cur = None
        for ln in lines:
            if IDPAT[kind].match(ln):
                if cur is not None: out.append(cur)
                cur = ln
            elif cur is not None and ln != '':
                cur += '\\n' + ln
        if cur is not None: out.append(cur)
    return [r.split('\t') for r in out]


def load(kind):
    d = {}
    for c in rows(kind):
        t = c[TCOL[kind]] if len(c) > TCOL[kind] else ''
        d[c[0]] = t.strip()
    return d


def originals(kind):
    f = {'음성자막': 'voice_ja.tsv', '브리핑막간': 'pages_ja_full.tsv', '메뉴그림': 'ui_ja.tsv'}[kind]
    ls = open(os.path.join(ROOT, 'work', 'text', f), encoding='utf-8').read().split('\n')[1:]
    return {l.split('\t')[0]: l.split('\t') for l in ls if l}


TERMS = {'ゴア': r'고아|고어|GOA|고와', 'ドナー': r'도나|도너|도나아', 'ザイコフ': r'자이코프|자이코후|다이코프', 'テラード': r'테라드|테라도|테라아도',
         'オヴァン': r'오반|오방|오반느|오바안', 'ネリー': r'네리|넬리', 'スコルビオ': r'스콜피오|스코르비오|스콜비오', 'シャドウ': r'섀도우|섀도|쉐도우|샤도우',
         'アサルト': r'어설트|아사울트|어썰트|아살트', '赤い蠍': r'붉은 전갈|붉은전갈|빨간 전갈', '八惑星': r'8행성|팔행성|8혹성|여덟 행성',
         'ニッタ': r'닛타|니타', 'シド': r'시드', 'ディオン': r'디온', 'ヒルダ': r'힐다', 'リディア': r'리디아', 'ライル': r'라일'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for kind in ('음성자막', '브리핑막간', '메뉴그림'):
        tr = load(kind); org = originals(kind)
        miss = [i for i in org if i not in tr]; extra = [i for i in tr if i not in org]; empty = [i for i in org if i in tr and not tr[i]]
        print('%s: 원본 %d · 받은 %d · 빠진 id %d · 남는 id %d · 빈 번역 %d' % (kind, len(org), len(tr), len(miss), len(extra), len(empty)), miss[:5], extra[:5], empty[:8])
    print('\n용어 변형(전체)')
    alltr = {**load('음성자막'), **load('브리핑막간'), **load('메뉴그림')}
    for jp, pat in TERMS.items():
        c = collections.Counter(m.group() for t in alltr.values() for m in re.finditer(pat, t))
        if c: print(' ', jp, dict(c))


if __name__ == '__main__':
    main()
