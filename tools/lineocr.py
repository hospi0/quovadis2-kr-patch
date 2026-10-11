# -*- coding: utf-8 -*-
r"""그림 글 줄 단위 OCR 다수결(2026-10-11) — work/zimg/{F,L}*.png(브리핑 쪽·막간 띠)
  줄(18px 간격, 첫 줄 y=4)마다 크기·번짐 변형 8개를 Windows 일본어 OCR → 글자 가로 가운데로 묶어(14px 칸) 묶음마다 다수결.
  → work/text/pages_ja.tsv(쪽 · 줄 · 판독) + 혼동 바로잡기(輓/戟→戦 · 丁→す 등)
  python tools/lineocr.py [prep|run|vote]
"""
import collections, glob, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'work', 'zimg'); OCR = os.path.join(ROOT, 'work', 'ocr3')
VAR = [(3, 0), (4, 0), (5, 0), (6, 0), (5, 1), (6, 1), (8, 2), (10, 2)]
PAD = 30


def pages(): return sorted(f for f in glob.glob(os.path.join(SRC, '*.png')) if os.path.basename(f)[0] in 'FL')


def rows(p):
    h = p.shape[0]; out = []
    for r in range(16):
        y = 4 + 18 * r
        if y >= h: break
        out.append((r, y))
    return out


def prep():
    os.makedirs(OCR, exist_ok=True)
    for f in glob.glob(os.path.join(OCR, '*')): os.remove(f)
    n = 0
    for f in pages():
        nm = os.path.basename(f)[:-4]; p = np.array(Image.open(f)) > 0
        for r, y in rows(p):
            strip = p[max(0, y - 2):y + 14]
            if not strip.any(): continue
            for S, bl in VAR:
                im = Image.fromarray(np.where(strip, 0, 255).astype(np.uint8)).resize((strip.shape[1] * S, strip.shape[0] * S), Image.NEAREST)
                if bl: im = im.filter(ImageFilter.GaussianBlur(bl))
                bg = Image.new('L', (im.width + 2 * PAD, im.height + 2 * PAD), 255); bg.paste(im, (PAD, PAD))
                bg.save(os.path.join(OCR, 'img_%s_r%02d_s%02d_b%d.png' % (nm, r, S, bl))); n += 1
    print('줄 그림', n)


def run():
    subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'winocr.ps1'), '-Dir', OCR], check=True, stdout=subprocess.DEVNULL)


FIX = [('輓', '戦'), ('戟', '戦'), ('丘陸', '丘陵'), ('イ主', '住'), ('寄襲', '奇襲')]


def vote():
    got = collections.defaultdict(list)                                # (쪽, 줄) → [(x, 글자, 변형)]
    for t in glob.glob(os.path.join(OCR, 'img_*.txt')):
        m = re.match(r'img_(.+)_r(\d+)_s(\d+)_b(\d)\.txt', os.path.basename(t)); nm, r, S, bl = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        for ln in open(t, encoding='utf-8').read().splitlines():
            if not ln.strip(): continue
            w, x, y, ww, h = ln.split('\t'); x, ww = float(x), float(ww)
            for j, ch in enumerate(w):
                got[(nm, r)].append(((x + ww * (j + 0.5) / len(w) - PAD) / S, ch, (S, bl)))
    out = []
    for f in pages():
        nm = os.path.basename(f)[:-4]; p = np.array(Image.open(f)) > 0
        for r, y in rows(p):
            strip = p[max(0, y - 2):y + 14]
            if not strip.any():
                out.append((nm, r, '')); continue
            pts = sorted(got.get((nm, r), []))
            # 묶기: 가로 가운데가 5px 안이면 같은 글자
            cl = []
            for x, ch, v in pts:
                if cl and x - cl[-1][-1][0] < 5: cl[-1].append((x, ch, v))
                else: cl.append([(x, ch, v)])
            s = ''
            for c in cl:
                vs = {}
                for x, ch, v in c: vs.setdefault(v, ch)                 # 변형마다 한 표
                if len(vs) * 2 < len(VAR) - 1: continue                 # 표 적으면(3표 미만) 지어낸 것
                s += collections.Counter(vs.values()).most_common(1)[0][0]
            out.append((nm, r, s))
    # 혼동 바로잡기
    res = []
    for nm, r, s in out:
        for a, b in FIX: s = s.replace(a, b)
        s = re.sub(r'(?<=[぀-ゟ])丁|丁(?=[぀-ゟ])', 'す', s)
        res.append((nm, r, s))
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', 'pages_ja.tsv'), 'w', encoding='utf-8', newline='\n') as fo:
        fo.write('쪽\t줄\t판독\n')
        for nm, r, s in res: fo.write('%s\t%d\t%s\n' % (nm, r, s))
    print('줄', len(res))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'prep': prep, 'run': run, 'vote': vote}[sys.argv[1]]()
