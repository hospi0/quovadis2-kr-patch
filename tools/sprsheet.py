# -*- coding: utf-8 -*-
r"""스테이트 화면의 VDP1 스프라이트 전부 → 확대 시트 + 디스크 파일 자리(2026-10-11, 미추출 그림 찾기).
  python tools/sprsheet.py 스테이트 출력.png
  색: 4비트 LUT/뱅크는 회색 단계(값×17), 8비트·RGB 는 실제에 가깝게. 파일 자리 = 텍스처 바이트를 디스크 .Z/.BIN 에서 검색.
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import state, vdp1, disc

_IDX = None


def index(k=1):
    global _IDX
    if _IDX is None:
        _IDX = []
        for n, l, s in disc.files(k):
            if s < 64 or not (n.endswith('.Z') or n.endswith('.BIN')) or '/WD' in n: continue
            _IDX.append((n, disc.read(n, k)))
    return _IDX


def tex(V, sp):
    mode = (sp['pmod'] >> 3) & 7; w, h = sp['w'], sp['h']
    if w == 0 or h == 0: return None, mode, b''
    if mode in (0, 1):
        n = w * h // 2; raw = V[sp['src']:sp['src'] + n]
        if len(raw) < n: return None, mode, raw
        b = np.frombuffer(raw, np.uint8); p = np.zeros(w * h, np.uint8); p[0::2] = b >> 4; p[1::2] = b & 15
        return (p.reshape(h, w) * 17).astype(np.uint8), mode, raw
    if mode in (2, 3, 4):
        n = w * h; raw = V[sp['src']:sp['src'] + n]
        if len(raw) < n: return None, mode, raw
        return np.frombuffer(raw, np.uint8).reshape(h, w).copy(), mode, raw
    n = w * h * 2; raw = V[sp['src']:sp['src'] + n]
    if len(raw) < n: return None, mode, raw
    a = np.frombuffer(raw, '>u2').reshape(h, w)
    g = (((a & 31) + ((a >> 5) & 31) + ((a >> 10) & 31)) * 255 // 93).astype(np.uint8)
    return g, mode, raw


def main(st, out):
    sys.stdout.reconfigure(encoding='utf-8')
    V = state.ram(st)['V1']
    seen = {}; rows = []
    for a, w in vdp1.cmds(V):
        if (w[0] & 15) > 2: continue
        sp = vdp1.sprite(w)
        key = (sp['src'], sp['w'], sp['h'])
        if key in seen: continue
        px, mode, raw = tex(V, sp)
        if px is None or not px.any(): continue
        where = ''
        probe = raw[:64]
        if len(set(probe)) > 3:
            for n, d in index():
                o = d.find(raw)
                if o >= 0: where = '%s 0x%X' % (n, o); break
        seen[key] = 1
        rows.append((sp, mode, px, where))
        print('%05X %3dx%-3d 모드 %d 화면(%d,%d) %s' % (sp['src'], sp['w'], sp['h'], mode, sp['x'], sp['y'], where))
    S = 3; W = 1600; x = y = 0; rh = 0; pos = []
    for sp, mode, px, where in rows:
        iw = max(px.shape[1] * S, 150); ih = px.shape[0] * S + 28
        if x + iw > W: x = 0; y += rh + 6; rh = 0
        pos.append((x, y)); x += iw + 8; rh = max(rh, ih)
    sh = Image.new('RGB', (W, y + rh + 6), (40, 0, 60)); dr = ImageDraw.Draw(sh)
    for (sp, mode, px, where), (x, y) in zip(rows, pos):
        im = Image.fromarray(px).resize((px.shape[1] * S, px.shape[0] * S), Image.NEAREST)
        sh.paste(im, (x, y + 28))
        dr.text((x, y), '%05X %dx%d m%d' % (sp['src'], sp['w'], sp['h'], mode), fill=(255, 255, 0))
        dr.text((x, y + 13), where.replace('/S1/', '')[:24], fill=(120, 255, 120))
    sh.save(out); print(out, sh.size, len(rows))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
