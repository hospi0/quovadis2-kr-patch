# -*- coding: utf-8 -*-
r"""하스피 번역 병합(2026-10-11) — my files/번역 → work/text/{voice,pages,ui}_ko.tsv (id · 번역)
  ★쓰는 순간 규칙 강제: 용어 통일(하스피 결정 2026-10-11) · 문장부호 뒤 공백 삭제 · 가나·한자 남음 검사(GOA·α 등 허용).
  용어: ゴア=고아 · ドナー=도나 · ネリー=네리 · スコルビオ=스콜피오 · アサルト=어설트 · 八惑星=8행성 · シャドウ=섀도 · ザイコフ=자이코프 · 赤い蠍=붉은 전갈
  python tools/merge_tr.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import load_tr

TERM = [(r'고어', '고아'), (r'ー', '~'), (r'・', '·'), (r'도너', '도나'), (r'넬리', '네리'), (r'스콜비오|스코르비오', '스콜피오'),
        (r'아사울트|어썰트', '어설트'), (r'팔행성|팔혹성|8혹성', '8행성'), (r'양륙정', '상륙정'), (r'에어리어', '에리어'), (r'섀도우|쉐도우|샤도우', '섀도'), (r'다이코프', '자이코프'), (r'빨간 전갈', '붉은 전갈'),
        (r'\(凧\)', ''), (r'무상\(無傷\) ?상태로', '흠집 없이'), (r' +·', '·')]
TAG = re.compile(r'\[[^\]\n]*\]')                                       # ★화자 표지 [불명] 등 — 자막에 나오면 안 됨(2026-10-11 실기)
FIX = {   # 하스피 손질(2026-10-11)
    'WD000/V0C04#1_0': '좋아!',
    'WD000/V0C28#1_1': '맞췄어!',
    'WD000/V0C34#0_1': '적기 격추!가자!',
}
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) +(?=\S)')
KANA = re.compile(r'[぀-ヿ一-鿿]')


def norm(t):
    t = TAG.sub('', t)
    for a, b in TERM: t = re.sub(a, b, t)
    parts = t.split('\\n')
    parts = [PUNCT_SP.sub(r'\1', p).strip() for p in parts]
    return '\\n'.join(parts)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for kind, f in (('음성자막', 'voice_ko.tsv'), ('브리핑막간', 'pages_ko.tsv'), ('메뉴그림', 'ui_ko.tsv')):
        tr = load_tr.load(kind); bad = []
        with open(os.path.join(ROOT, 'work', 'text', f), 'w', encoding='utf-8', newline='\n') as fo:
            fo.write('id\t번역\n')
            for i, t in tr.items():
                t2 = norm(FIX.get(i, t))
                if KANA.search(t2) or '[' in t2 or ']' in t2: bad.append((i, t2))
                fo.write('%s\t%s\n' % (i, t2))
        print('%s → work/text/%s %d줄 · 가나·한자 남음 %d' % (kind, f, len(tr), len(bad)))
        for i, t in bad[:15]: print('   ', i, t[:80])


if __name__ == '__main__':
    main()
