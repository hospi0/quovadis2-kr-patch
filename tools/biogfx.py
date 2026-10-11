# -*- coding: utf-8 -*-
r"""병사 소개 판(2026-10-11) — S1/S??.R = 얼굴 96×72 8비트(6,912 B) + 소개 판 152×192 4비트(값 1, 14,592 B). 두 장 같은 내용(51개).
  원래 배치: 1줄(이름·특기) 7‥18 · 2줄(출신·나이) 26‥37 · 본문 45‥ 16px 간격 최대 9줄, 글자 12px, 가로 7‥151.
  번역 work/text/bio_ko.tsv(id·이름·특기·출신·나이·소개). 본문은 띄어쓰기 단위로 접고, 9줄 넘으면 줄 간격 14 → 갈무리9(13 간격)로.
  build(장) → {'/S1/S01.R': 바이트, …} · python tools/biogfx.py → work/probe/bio_kr.png
"""
import os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

FD = r'C:\claude\utils\font\Galmuri-v2.40.3'
F11 = ImageFont.truetype(os.path.join(FD, 'Galmuri11.ttf'), 12)
F9 = ImageFont.truetype(os.path.join(FD, 'Galmuri9.ttf'), 10)
OFF = 96 * 72; W, H = 152, 192; X0, X1 = 7, 151
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) +(?=\S)')


def tr():
    out = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'bio_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 6: out[c[0]] = c[1:6]
    return out


def tw(s, f): return ImageDraw.Draw(Image.new('1', (8, 8))).textlength(s, font=f)


def wrap(text, f, w):
    out, cur = [], ''
    for word in PUNCT_SP.sub(r'\1', text).split(' '):
        t = (cur + ' ' + word) if cur else word
        if tw(t, f) <= w: cur = t; continue
        if cur: out.append(cur)
        while tw(word, f) > w:                                          # 한 낱말이 줄보다 길면 글자 단위
            k = len(word)
            while tw(word[:k], f) > w: k -= 1
            out.append(word[:k]); word = word[k:]
        cur = word
    if cur: out.append(cur)
    return out


def panel(name, spec, origin, age, body):
    im = Image.new('1', (W, H), 0); dr = ImageDraw.Draw(im)
    def put(x, ytop, s, f, right=False):
        l, t, r, b = dr.textbbox((0, 0), s, font=f)
        dr.text(((X1 - (r - l) if right else x) - l, ytop - 1), s, font=f, fill=1)
    for (ya, la, ra) in ((7, '이름 ' + name, '특기 ' + spec), (26, '출신 ' + origin, '나이 ' + age)):
        f = F11 if tw(la, F11) + tw(ra, F11) + 6 <= X1 - X0 else F9      # 길면 이 줄만 갈무리9
        assert tw(la, f) + tw(ra, f) + 4 <= X1 - X0, ('머리줄 넘침', la, ra)
        put(X0, ya + (1 if f is F9 else 0), la, f); put(0, ya + (1 if f is F9 else 0), ra, f, right=True)
    for f, pitch in ((F11, 16), (F11, 14), (F9, 13)):
        lines = wrap(body, f, X1 - X0)
        if 45 + pitch * (len(lines) - 1) + 12 <= H: break
    else: raise AssertionError(('소개 넘침', name, len(lines)))
    for i, s in enumerate(lines): put(X0, 45 + i * pitch, s, f)
    return np.array(im, np.uint8)


def pack(p):
    f = p.ravel(); return bytes(((f[0::2] << 4) | f[1::2]).tolist())


def build(disk, log=print):
    t = tr(); out = {}
    for n, l, s in disc.files(disk):
        if not (n.startswith('/S1/S') and n.endswith('.R')): continue
        k = n[4:7]
        d = bytearray(disc.read(n, disk)); assert len(d) == OFF + W * H // 2, n
        old = np.frombuffer(bytes(d[OFF:]), np.uint8)
        assert set(np.unique(np.concatenate([old >> 4, old & 15])).tolist()) <= {0, 1}, n
        d[OFF:] = pack(panel(*t[k])); out[n] = bytes(d)
    log('병사 소개 판(장 %d): %d' % (disk, len(out)))
    return out


def preview(out):
    t = tr(); tiles = []
    for k in sorted(t):
        p = panel(*t[k]); tiles.append((k, (p * 255).astype(np.uint8)))
    cols = 6; sh = Image.new('L', (cols * (W * 2 + 8), ((len(tiles) + cols - 1) // cols) * (H * 2 + 14)), 40); dr = ImageDraw.Draw(sh)
    for i, (k, p) in enumerate(tiles):
        x = (i % cols) * (W * 2 + 8); y = (i // cols) * (H * 2 + 14)
        sh.paste(Image.fromarray(p).resize((W * 2, H * 2), Image.NEAREST), (x, y + 12)); dr.text((x, y), k, fill=255)
    sh.save(out); print(out, len(tiles))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    preview(os.path.join(ROOT, 'work', 'probe', 'bio_kr.png'))
