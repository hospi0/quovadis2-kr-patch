# -*- coding: utf-8 -*-
r"""판독 검토 시트(2026-10-11) — 쪽 그림(2배) 옆에 판독 줄(MS 고딕)을 같은 높이로 → work/ocr_review/sheet_NN.png"""
import collections, csv, glob, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
F = ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc', 22)


def main(per=6, prefix=''):
    rows = collections.defaultdict(dict)
    for r in list(csv.reader(open(os.path.join(ROOT, 'work', 'text', 'pages_ja.tsv'), encoding='utf-8'), delimiter='\t'))[1:]:
        rows[r[0]][int(r[1])] = r[2]
    names = [n for n in sorted(rows) if n.startswith(prefix)]
    out = os.path.join(ROOT, 'work', 'ocr_review'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 'sheet_*.png')): os.remove(f)
    blocks = []
    for n in names:
        p = Image.open(os.path.join(ROOT, 'work', 'zimg', n + '.png')); S = 2
        im = p.resize((p.width * S, p.height * S), Image.NEAREST)
        W = im.width + 30 + 22 * 25; H = im.height + 30
        b = Image.new('L', (W, H), 255); b.paste(im, (0, 26)); d = ImageDraw.Draw(b)
        d.text((0, 0), n, font=F, fill=0)
        for r, s in rows[n].items():
            d.text((im.width + 20, 26 + (4 + 18 * r) * S - 4), '%d %s' % (r, s), font=F, fill=0)
        blocks.append(b)
    k = 0
    for i in range(0, len(blocks), per):
        bs = blocks[i:i + per]; W = max(b.width for b in bs); H = sum(b.height + 6 for b in bs)
        s = Image.new('L', (W, H), 160); y = 0
        for b in bs: s.paste(b, (0, y)); y += b.height + 6
        s.save(os.path.join(out, 'sheet_%02d.png' % k)); k += 1
    print('시트', k, '쪽', len(blocks))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6, sys.argv[2] if len(sys.argv) > 2 else '')
