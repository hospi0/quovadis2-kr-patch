# -*- coding: utf-8 -*-
r"""브리핑(S1/F???.Z)·막간(S1/L???.Z) 글 쪽 그림을 한글로 다시 그리기(2026-10-11).
  쪽 = 4비트 항목 168×168 · 120×168(브리핑) · 288×56(막간), 색인 0 바탕 · 1 글자. 줄 18px(첫 줄 y=4) — 원본 격자 그대로.
  .Z 마다 글 쪽(항목 순서, 같은 그림은 한 번)을 이어 한 글로 보고(tools/pages_tsv.py 와 같은 묶음), 번역(work/text/pages_ko.tsv)을
  같은 쪽 수에 다시 흘려 넣는다(«\n» 강제 줄바꿈 · 빈 줄 = 문단). 같은 그림을 쓰는 항목은 모두 같은 새 그림.
  글꼴 갈무리11(12px 비트맵). 넘치면(줄 수 > 쪽 수×줄) 오류.
  build(장) → {'/S1/F001.Z': 바이트, …} · python tools/pagegfx.py → work/probe/pages_kr/*.png 미리보기(원본|한글)
"""
import collections, csv, hashlib, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, zspr

FONT = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf'
SIZES = ((168, 168), (120, 168), (288, 56))
Y0, PITCH = 4, 18
FONT_C = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Condensed.ttf'   # 넘치는 파일만 좁은꼴
_FONTS = [ImageFont.truetype(FONT, 12), ImageFont.truetype(FONT_C, 12)]
_F = _FONTS[0]
_D = ImageDraw.Draw(Image.new('1', (8, 8)))


def tw(s): return _D.textlength(s, font=_F)


def use(k):
    global _F
    _F = _FONTS[k]


def texts():
    ko = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'pages_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 2: ko[c[0]] = c[1]
    fid = {}
    for r in list(csv.reader(open(os.path.join(ROOT, 'work', 'text', 'pages_ja_full.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        for f in r[2].split(','): fid[f] = r[0]
    return ko, fid


def wrap(text, W):
    """→ 줄 목록('' = 빈 줄)"""
    out = []
    for para in text.split('\\n'):
        para = para.strip()
        if not para: out.append(''); continue
        cur = ''
        # 낱말 = 띄어쓰기 단위, 단 문장부호 뒤(부호 뒤 공백을 지웠으므로)에서도 끊을 수 있게 «붙는 조각»으로 나눔
        toks = []
        for k, w in enumerate(para.split(' ')):
            for j, piece in enumerate(re.findall(r'[^,.!?…]*[,.!?…]+|[^,.!?…]+', w)):
                toks.append((piece, k > 0 and j == 0))
        for w, sp in toks:
            t = (cur + (' ' if sp else '') + w) if cur else w
            if tw(t) <= W: cur = t; continue
            if cur: out.append(cur); cur = ''
            while tw(w) > W:
                k = len(w)
                while tw(w[:k]) > W: k -= 1
                out.append(w[:k]); w = w[k:]
            cur = w
        out.append(cur)
    while out and not out[-1]: out.pop()
    return out


def render(lines, W, H):
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
    for r, s in enumerate(lines):
        if s: d.text((0, Y0 + r * PITCH - 1), s, font=_F, fill=1)
    return np.array(im, np.uint8)


def pack4(p):
    f = p.ravel(); return bytes(((f[0::2] << 4) | f[1::2]).tolist())


def file_pages(d):
    """→ [(md5, [항목…], (W,H))] 글 쪽(항목 순서, 같은 그림 묶음)"""
    order = []; by = {}
    for e in zspr.entries(d):
        if (e['w'], e['h']) not in SIZES or e['bpp'] != 4 or 0x1000 + e['off'] + e['size'] > len(d): continue
        p = zspr.pixels(d, e)
        if p.max() == 0 or not set(np.unique(p)) <= {0, 1, 15}: continue
        h = hashlib.md5(p.tobytes()).hexdigest()
        if h not in by: by[h] = []; order.append((h, (e['w'], e['h'])))
        by[h].append(e)
    return [(h, by[h], wh) for h, wh in order]


def build(disk, log=print, preview=None):
    ko, fid = texts(); out = {}; errs = []
    for n, l, s in disc.files(disk):
        fn = n.split('/')[-1]
        if not (n.startswith('/S1/') and fn[0] in 'FL' and fn.endswith('.Z')): continue
        key = fn[:-2]
        if key not in fid: continue
        d = bytearray(disc.read(n, disk)); pages = file_pages(bytes(d))
        if not pages: continue
        W, H = pages[0][2]; rows = (H - Y0 - 12) // PITCH + 1
        cap = rows * len(pages)
        for fk in (0, 1):
            use(fk); lines = wrap(ko[fid[key]], W)
            if len(lines) <= cap: break
        if len(lines) > cap:
            use(0); errs.append('%s 줄 %d > %d쪽×%d줄' % (key, len(lines), len(pages), rows)); continue
        if fk: log('  좁은꼴', key)
        for k, (h, es, wh) in enumerate(pages):
            chunk = lines[k * rows:(k + 1) * rows]
            while chunk and not chunk[0] and k: chunk = chunk[1:]       # 쪽 첫 줄 빈 줄은 당김(마지막 쪽 남는 칸으로)
            px = render(chunk, *wh)
            org = zspr.pixels(bytes(d), es[0]); px[org == 15] = 15          # 15 색 표시는 원본 그대로
            b = pack4(px)
            for e in es:
                o = 0x1000 + e['off']; assert len(b) == e['size']; d[o:o + len(b)] = b
            if preview is not None: preview.append((key, k, zspr.pixels(disc.read(n, disk), es[0]), px))
        use(0); out[n] = bytes(d)
    for e in errs: log('⛔', e)
    assert not errs, '쪽 넘침'
    log('글 쪽 그림(장 %d): 파일 %d' % (disk, len(out)))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    prev = []
    build(1, preview=prev)
    od = os.path.join(ROOT, 'work', 'probe', 'pages_kr'); os.makedirs(od, exist_ok=True)
    groups = collections.OrderedDict()
    for key, k, a, b in prev: groups.setdefault(key, []).append((a, b))
    for key, ps in groups.items():
        Wd = max(a.shape[1] for a, b in ps) * 2 + 8; Hd = sum(a.shape[0] + 6 for a, b in ps)
        im = Image.new('L', (Wd, Hd), 90); y = 0
        for a, b in ps:
            im.paste(Image.fromarray((a * 255).astype(np.uint8)), (0, y)); im.paste(Image.fromarray((b * 255).astype(np.uint8)), (a.shape[1] + 8, y)); y += a.shape[0] + 6
        im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(od, key + '.png'))
    print('미리보기', od, len(groups))


if __name__ == '__main__':
    main()
