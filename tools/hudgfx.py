# -*- coding: utf-8 -*-
r"""전투 HUD 글자 그림(2026-10-11) — S1/HYO_01.Z(VDP1 VRAM 0xD4C0 에 통째로, 4비트, 파일 자리 = VRAM − 0xD4C0).
  전투 명령 32×16: 글자 값 3 + 오른쪽·아래 1px 그림자 값 2 (원본 글자 줄 1‥11, 그림자 12).
  우상단 상태 24×16: 한 색 값 1 (원본 글자 줄 5‥15).
  번역 work/text/gfx2_ko.tsv(HUD_*). build(장) → {'/S1/HYO_01.Z': 바이트} · python tools/hudgfx.py → work/probe/hud_kr.png
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

FD = r'C:\claude\utils\font\Galmuri-v2.40.3'
BOLD = ImageFont.truetype(os.path.join(FD, 'Galmuri11-Bold.ttf'), 12)
REG = ImageFont.truetype(os.path.join(FD, 'Galmuri11.ttf'), 12)
CMD = {'HUD_C01': 0x20C60, 'HUD_C02': 0x20D60, 'HUD_C03': 0x20E60, 'HUD_C04': 0x20F60, 'HUD_C05': 0x21060}
STAT = {'HUD_S01': 0x1F8E0, 'HUD_S02': 0x1F9A0, 'HUD_S03': 0x1FA60, 'HUD_S04': 0x1FB20, 'HUD_S05': 0x1FBE0, 'HUD_S06': 0x1FCA0, 'HUD_S07': 0x1FD60, 'HUD_S08': 0x1FE20}
SUB = {'HUD_W01': 0x21160, 'HUD_W02': 0x21220, 'HUD_W03': 0x212E0, 'HUD_W04': 0x213A0, 'HUD_W05': 0x21460}   # 무기 하위 명령 24×16(값 3 + 그림자 2)


def tr():
    out = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'gfx2_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 2: out[c[0]] = c[1]
    return out


def ink(text, font):
    """→ 잉크만 자른 0/1 배열"""
    im = Image.new('1', (80, 24), 0); ImageDraw.Draw(im).text((2, 2), text, font=font, fill=1)
    a = np.array(im, np.uint8); ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def get(d, off, w, h):
    b = np.frombuffer(d[off:off + w * h // 2], np.uint8); p = np.zeros(w * h, np.uint8)
    p[0::2] = b >> 4; p[1::2] = b & 15
    return p.reshape(h, w)


def put(d, off, p):
    f = p.ravel(); d[off:off + len(f) // 2] = bytes(((f[0::2] << 4) | f[1::2]).tolist())


def cmd_px(text, w=32, h=16, area=24, ytop=1, hh=11):
    g = ink(text, REG); gh, gw = g.shape
    assert gw <= area - 1 and gh <= hh, ('명령 글자 넘침', text, g.shape)
    p = np.zeros((h, w), np.uint8)
    x0 = (area - 1 - gw) // 2; y0 = ytop + (hh - gh) // 2              # 원본 글자 자리(가로 0‥23 · 세로 1‥11) 가운데
    sh = np.zeros((h, w), bool); sh[y0 + 1:y0 + 1 + gh, x0 + 1:x0 + 1 + gw] = g.astype(bool)
    p[sh] = 2; p[y0:y0 + gh, x0:x0 + gw][g.astype(bool)] = 3
    return p


def stat_px(text, w=24, h=16):
    g = ink(text, REG); gh, gw = g.shape
    assert gw <= 24 and gh <= 11, ('상태 글자 넘침', text, g.shape)
    p = np.zeros((h, w), np.uint8)
    x0 = (24 - gw) // 2; y0 = 5 + (11 - gh) // 2
    p[y0:y0 + gh, x0:x0 + gw][g.astype(bool)] = 1
    return p


def build(disk, log=print):
    t = tr(); d = bytearray(disc.read('/S1/HYO_01.Z', disk))
    n = 0
    for k, off in CMD.items():
        assert set(np.unique(get(d, off, 32, 16))) <= {0, 2, 3}, k
        put(d, off, cmd_px(t[k])); n += 1
    for k, off in STAT.items():
        assert set(np.unique(get(d, off, 24, 16))) <= {0, 1}, k
        put(d, off, stat_px(t[k])); n += 1
    for k, off in SUB.items():
        assert set(np.unique(get(d, off, 24, 16))) <= {0, 2, 3}, k
        put(d, off, cmd_px(t[k], w=24, area=24, ytop=1, hh=13)); n += 1
    log('HUD 그림(장 %d): HYO_01.Z 글자 %d개' % (disk, n))
    return {'/S1/HYO_01.Z': bytes(d)}


def preview(out):
    o = disc.read('/S1/HYO_01.Z', 1); k = build(1)['/S1/HYO_01.Z']
    pal = np.array([[0, 0, 0], [230, 230, 240], [40, 70, 160], [235, 235, 255]] + [[255, 0, 255]] * 12, np.uint8)
    S = 6; rows = []
    for ks, w in ((CMD, 32), (STAT, 24), (SUB, 24)):
        for key, off in ks.items():
            a = np.hstack([pal[get(o, off, w, 16)], np.full((16, 2, 3), 90, np.uint8), pal[get(k, off, w, 16)]])
            rows.append(Image.fromarray(a).resize((a.shape[1] * S, 16 * S), Image.NEAREST))
    W = max(r.width for r in rows); im = Image.new('RGB', (W * 2 + 20, (16 * S + 6) * ((len(rows) + 1) // 2)), (60, 0, 60))
    for i, r in enumerate(rows): im.paste(r, ((i % 2) * (W + 20), (i // 2) * (16 * S + 6)))
    im.save(out); print(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    preview(os.path.join(ROOT, 'work', 'probe', 'hud_kr.png'))


# ── 로딩 계기판 «起動»(2026-10-11) — S1/NL2.B = 앞 0x600(팔레트 등) + 88×48 8비트 계기판(METER.Z 0번과 글자 자리만 다름) ──
NL2_OFF = 0x600; NL2_BOX = (8, 5, 31, 16); NL2_COL = 241


def build_nl2(disk, log=print):
    import zspr
    t = tr(); d = bytearray(disc.read('/S1/NL2.B', disk))
    g = np.frombuffer(bytes(d[NL2_OFF:NL2_OFF + 88 * 48]), np.uint8).reshape(48, 88).copy()
    m = disc.read('/S1/METER.Z', disk); base = zspr.pixels(m, zspr.entries(m)[0])
    x0, y0, x1, y1 = NL2_BOX
    assert (g != base).any(axis=None) and not ((g != base)[:y0].any() or (g != base)[y1:].any()), '계기판 바탕이 METER 0 과 다름'
    g[y0:y1, x0:x1] = base[y0:y1, x0:x1]
    p = stat_px(t['HUD_K01'], w=24, h=16)                                # 상태 글자와 같은 모양(줄 5‥15)
    sub = p[5:16, 0:23] > 0
    g[y0:y1, x0:x1][sub] = NL2_COL
    d[NL2_OFF:NL2_OFF + 88 * 48] = g.tobytes()
    log('로딩 계기판(장 %d): NL2.B «%s»' % (disk, t['HUD_K01']))
    return {'/S1/NL2.B': bytes(d)}


# ── 작전 종료 «作戦終了»(2026-10-11) — S1/SYU.B = 팔레트 0x400(RGB555 512) + 128×24 8비트(@0x400) + 128×16 «MISSON COMPLETED»(@0x1000) ──
SYU_BOX = (19, 0, 86, 21)                                               # 글자 자리(빗금 오른쪽 ‥ 오른쪽 작은 표 앞)


def build_syu(disk, log=print):
    import struct, bggfx
    t = tr(); d = bytearray(disc.read('/S1/SYU.B', disk))
    c = np.array(struct.unpack('>512H', bytes(d[:0x400])))
    pal = np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], 1).astype(np.uint8)
    idx = np.frombuffer(bytes(d[0x400:0x400 + 128 * 24]), np.uint8).reshape(24, 128).astype(int)
    rgb = pal[idx]; orig = rgb.copy()
    x0, y0, x1, y1 = SYU_BOX
    rgb = bggfx.apply(rgb, SYU_BOX, t['HUD_E01'], dict(font='g14', pick=lambda px: px.min(axis=2) >= 40, aa=(bggfx.NB, 16), box=(x0, y0, x1, y1 + 2)))
    rgb[y0:y1, x0:x1][orig[y0:y1, x0:x1].min(axis=2) < 40] = rgb[y0:y1, x0:x1][orig[y0:y1, x0:x1].min(axis=2) < 40]
    ch = (rgb != orig).any(axis=2); ys, xs = np.nonzero(ch)
    cand = pal[1:256].astype(int); px = rgb[ys, xs].astype(int)
    out = idx.copy(); out[ys, xs] = ((px[:, None, :] - cand[None]) ** 2).sum(2).argmin(1) + 1
    bg = (rgb[ys, xs].max(axis=1) < 12); out[ys[bg], xs[bg]] = 0             # 거의 검정 = 바탕(0)
    d[0x400:0x400 + 128 * 24] = out.astype(np.uint8).tobytes()
    log('작전 종료 그림(장 %d): SYU.B «%s»' % (disk, t['HUD_E01']))
    return {'/S1/SYU.B': bytes(d)}
