# -*- coding: utf-8 -*-
r""".Z 스프라이트 묶음(2026-10-11) — VDP1 VRAM 에 통째로 실리는 그림 묶음.
  머리 0x1000(16 B × 256): +0 u16 깃발(0x20 = 8비트 · 0 = 4비트) · +2 u16 폭 · +4 u16 높이 · +8 u32 자료 위치(머리 뒤 기준) · 끝 FFFF…
  예) S1/F001.Z 브리핑: 144×216 8비트 지도 + 168×168 4비트 글 쪽(VRAM 0x30000+0x7980 에 그대로 = 브리핑 스테이트 확인).
"""
import struct
import numpy as np


def entries(d):
    out = []
    for i in range(0, 0x1000, 16):
        e = d[i:i + 16]
        if e[:4] == b'\xff\xff\xff\xff' or len(e) < 16: break
        fl, w, h = struct.unpack_from('>HHH', e, 0); off = struct.unpack_from('>I', e, 8)[0]
        bpp = 8 if fl & 0x20 else 4
        out.append(dict(i=i // 16, fl=fl, w=w, h=h, off=off, bpp=bpp, size=w * h * bpp // 8))
    return out


def pixels(d, e):
    o = 0x1000 + e['off']; b = np.frombuffer(d[o:o + e['size']], np.uint8)
    if e['bpp'] == 8: return b.reshape(e['h'], e['w']).copy()
    p = np.zeros(e['w'] * e['h'], np.uint8); p[0::2] = b >> 4; p[1::2] = b & 15
    return p.reshape(e['h'], e['w'])
