# -*- coding: utf-8 -*-
r"""옵션 화면 그림(2026-10-11) — S1/OPT.Z(.Z 스프라이트 묶음, tools/zspr.py).
  42  184×176 8비트(팔레트 CRAM 0x100‥) BGM·サウンド 하위판: インターミッション·作戦進行中·サウンド·ステレオ/モノラル·戻る
  46  216×104 8비트(팔레트 CRAM 0x400‥) 무비 재생판: ムービー再生·見たいムービーを選択してください
  51‥72 136×24 4비트 무비 제목(글자 값 1 + 가장자리 2‥4, 바탕 0) — 새로 그림.
  8비트 판: 팔레트로 RGB → tools/bggfx.apply(지우기·그리기) → 바뀐 화소만 같은 뱅크의 가장 가까운 색 번호(0 = 투명 제외).
  팔레트 work/opt/cram_opt.bin(옵션 스테이트 CRAM). 번역 work/text/gfx2_ko.tsv(OPT2_* · MOV_*).
  build(장) → {'/S1/OPT.Z': 바이트} · python tools/optgfx.py → work/probe/opt_kr.png
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, zspr, bggfx

_c = np.array(struct.unpack('>2048H', open(os.path.join(ROOT, 'work', 'opt', 'cram_opt.bin'), 'rb').read()))
PAL = np.stack([(_c & 31) << 3, ((_c >> 5) & 31) << 3, ((_c >> 10) & 31) << 3], 1).astype(np.uint8)
_W = bggfx.white


def dim(px):              # 꺼진 항목의 흐린 회색 글자(어두운 남색 바탕)
    return px[..., 0] >= 20                                          # 바탕은 R = 0


_L = dict(font='g11', pick=_W, align='l')
PANELS = {
    42: (0x100, [
        ((32, 26, 146, 42), 'OPT2_1', dict(_L, pick=lambda px: px.min(axis=2) >= 90, grow=2, box=(34, 26, 160, 42))),
        ((32, 59, 98, 75), 'OPT2_2', dict(_L, pick=lambda px: px.min(axis=2) >= 90, grow=2, box=(34, 59, 160, 75))),
        ((28, 93, 90, 110), 'OPT2_3', dict(_L, box=(30, 93, 160, 110))),
        ((30, 123, 90, 139), 'OPT2_4', dict(_L, pick=dim, box=(34, 123, 92, 139))),
        ((110, 123, 165, 139), 'OPT2_5', dict(_L, pick=dim, box=(112, 123, 170, 139))),
        ((40, 151, 90, 168), 'OPT2_6', dict(font='g11', pick=dim, stamp=(48, 152, 0x1A40))),   # 선택 때 덮이는 «돌아가기» 32×16(OPT.Z @0x1A40, 화면 160,184)과 같은 자리·모양으로(하스피 «겹침»)
    ]),
    46: (0x400, [
        ((28, 13, 108, 27), 'OPT3_1', dict(_L, box=(30, 13, 150, 27))),
        ((8, 39, 172, 53), 'OPT3_2', dict(font='g11', pick=_W, box=(6, 38, 178, 54))),
    ]),
}
MOV = list(range(51, 73))


def tr():
    return bggfx.tr()


def panel(d, e, bank, jobs, t):
    idx = zspr.pixels(d, e).astype(int); rgb = PAL[bank + idx]; orig = rgb.copy()
    for box, key, cfg in jobs:
        if cfg.get('stamp'):                                            # 지우고, 겹쳐 그리는 스프라이트의 글자 모양을 그 자리에 흐린 색으로
            x0, y0, x1, y1 = box; sx, sy, soff = cfg['stamp']
            sub = rgb[y0:y1, x0:x1]; col = sub[cfg['pick'](sub)].mean(axis=0)
            rgb = bggfx.apply(rgb, box, '', dict(cfg, erase=True))
            se = [x for x in zspr.entries(d) if 0x1000 + x['off'] == soff][0]
            m = zspr.pixels(d, se) != 0
            rgb[sy:sy + m.shape[0], sx:sx + m.shape[1]][m] = col
            continue
        rgb = bggfx.apply(rgb, box, t[key], cfg)
    ch = (rgb != orig).any(axis=2)
    cand = PAL[bank + 1:bank + 256].astype(int)
    out = idx.copy()
    ys, xs = np.nonzero(ch)
    px = rgb[ys, xs].astype(int)
    dd = ((px[:, None, :] - cand[None, :, :]) ** 2).sum(axis=2)
    out[ys, xs] = dd.argmin(axis=1) + 1
    return out


def title(text, w=136, h=24):
    f = ImageFont.truetype(*bggfx.FONTS['g11'])
    im = Image.new('1', (w, h), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), text, font=f); assert r - l <= w - 8, ('제목 넘침', text, r - l)
    dr.text((4 - l, 0), text, font=f, fill=1)
    m = np.array(im, bool); ys = np.nonzero(m.any(axis=1))[0]
    g = m[ys.min():ys.max() + 1]; out = np.zeros((h, w), np.uint8); y = 7 + (13 - g.shape[0]) // 2
    out[y:y + g.shape[0]][g] = 1
    return out


def put(d, e, px):
    o = 0x1000 + e['off']; f = px.ravel().astype(np.uint8)
    if e['bpp'] == 8: d[o:o + len(f)] = f.tobytes()
    else: d[o:o + len(f) // 2] = bytes(((f[0::2] << 4) | f[1::2]).tolist())


def build(disk, log=print, base=None):
    t = tr(); d = bytearray((base or {}).get('/S1/OPT.Z') or disc.read('/S1/OPT.Z', disk)); E = zspr.entries(bytes(d))   # uigfx(OPT_00‥08) 결과 위에
    for i, (bank, jobs) in PANELS.items(): put(d, E[i], panel(bytes(d), E[i], bank, jobs, t))
    for i in MOV:
        assert set(np.unique(zspr.pixels(bytes(d), E[i])).tolist()) <= {0, 1, 2, 3, 4}, i
        put(d, E[i], title(t['MOV_%d' % i]))
    log('옵션 그림(장 %d): 판 %d · 무비 제목 %d' % (disk, len(PANELS), len(MOV)))
    return {'/S1/OPT.Z': bytes(d)}


def preview(out):
    o = disc.read('/S1/OPT.Z', 1); k = build(1)['/S1/OPT.Z']; E = zspr.entries(o)
    rows = []
    for i, (bank, jobs) in PANELS.items():
        a = PAL[bank + zspr.pixels(o, E[i]).astype(int)]; b = PAL[bank + zspr.pixels(k, E[i]).astype(int)]
        rows.append(np.hstack([a, np.full((a.shape[0], 4, 3), 255, np.uint8), b]))
    for i in MOV:
        a = (zspr.pixels(o, E[i]) * 60).clip(0, 255).astype(np.uint8); b = (zspr.pixels(k, E[i]) * 60).clip(0, 255).astype(np.uint8)
        g = np.hstack([a, np.full((24, 4), 255, np.uint8), b]); rows.append(np.dstack([g, g, g]))
    W = max(r.shape[1] for r in rows); H = sum(r.shape[0] + 4 for r in rows)
    sh = np.full((H, W, 3), 40, np.uint8); y = 0
    for r in rows: sh[y:y + r.shape[0], :r.shape[1]] = r; y += r.shape[0] + 4
    Image.fromarray(sh).resize((W * 2, H * 2), Image.NEAREST).save(out); print(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    preview(os.path.join(ROOT, 'work', 'probe', 'opt_kr.png'))
