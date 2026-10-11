# -*- coding: utf-8 -*-
r"""그림 글(브리핑 F*.Z 쪽 · 막간 L*.Z 띠) 판독(2026-10-11).
  격자: 칸 가로 14px(잉크는 칸 왼쪽 −1 부터) · 줄 18px(첫 줄 잉크 y=4). 칸 그림 = [y0−1, y0+13) × [x0−1, x0+14).
  ①페이지마다 4배로 흰 바탕에 그려 Windows 일본어 OCR(tools/winocr.ps1) ②인식 글자 가운데로 칸 짚기 ③글리프(칸 그림 md5)별 다수결
  python tools/pageocr.py prep | run | vote
"""
import collections, glob, hashlib, json, os, subprocess, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'zimg'); OCR = os.path.join(ROOT, 'work', 'ocr')
S = 4; PX, PY, Y0 = 14, 18, 4


def pages():
    return sorted(f for f in glob.glob(os.path.join(SRC, '*.png')) if os.path.basename(f)[0] in 'FL')


def cells(p):
    """→ {(행, 열): 칸 그림(bool 14×15)} — 잉크 있는 칸만"""
    h, w = p.shape; out = {}
    pp = np.zeros((h + 20, w + 20), bool); pp[1:h + 1, 1:w + 1] = p
    for r in range((h - Y0 + 4) // PY + 1):
        for c in range(w // PX + 1):
            y = Y0 + r * PY; x = c * PX
            g = pp[y:y + 14, x:x + 14]
            if g.any(): out[(r, c)] = g
    return out


def norm(g):
    """좌우 빈 열만 잘라 가로 위치 차이 없앰(세로는 그대로 — 。、 구별)"""
    cs = np.where(g.any(0))[0]
    return g[:, cs[0]:cs[-1] + 1]


def gid(g):
    g = norm(g); return hashlib.md5(np.packbits(g).tobytes() + bytes(g.shape)).hexdigest()[:12]


def prep():
    os.makedirs(OCR, exist_ok=True)
    for f in pages():
        p = np.array(Image.open(f)) > 0
        im = Image.fromarray(np.where(p, 0, 255).astype(np.uint8)).resize((p.shape[1] * S, p.shape[0] * S), Image.NEAREST)
        bg = Image.new('L', (im.width + 80, im.height + 80), 255); bg.paste(im, (40, 40))
        bg.save(os.path.join(OCR, 'img_' + os.path.basename(f)))
    print('준비', len(pages()))


def run():
    subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'winocr.ps1'), '-Dir', OCR], check=True)


def vote():
    votes = collections.defaultdict(collections.Counter); glyph = {}; layout = {}
    for f in pages():
        nm = os.path.basename(f)[:-4]
        p = np.array(Image.open(f)) > 0; cs = cells(p)
        lay = {}
        for k, g in cs.items():
            i = gid(g); glyph[i] = norm(g); lay[k] = i
        layout[nm] = {'%d,%d' % k: v for k, v in lay.items()}
        t = os.path.join(OCR, 'img_' + nm + '.txt')
        if not os.path.exists(t): continue
        for ln in open(t, encoding='utf-8').read().splitlines():
            if not ln.strip(): continue
            word, x, y, w, h = ln.split('\t'); x, y, w, h = map(float, (x, y, w, h))
            n = len(word)
            for j, ch in enumerate(word):
                cx = (x + w * (j + 0.5) / n - 40) / S; cy = (y + h / 2 - 40) / S
                r = int(round((cy - Y0 - 6) / PY)); c = int(cx // PX)
                if (r, c) in lay: votes[lay[(r, c)]][ch] += 1
    best = {i: (votes[i].most_common(1)[0][0] if votes[i] else '?') for i in glyph}
    json.dump({'best': best, 'votes': {i: dict(v) for i, v in votes.items()}, 'layout': layout}, open(os.path.join(OCR, 'vote.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    np.save(os.path.join(OCR, 'glyphs.npy'), {i: np.packbits(g) for i, g in glyph.items()}, allow_pickle=True)
    nv = sum(1 for i in glyph if votes[i])
    print('글리프 %d · 표 받은 것 %d' % (len(glyph), nv))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'prep': prep, 'run': run, 'vote': vote}[sys.argv[1]]()
