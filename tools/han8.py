# -*- coding: utf-8 -*-
r"""쿠오바디스 2 8×8 한글 글리프(2026-10-11) — AWW hangul8comp 바탕 + ㅔ/ㅖ 구별.
  hangul8comp 은 ㅔ=ㅐ·ㅖ=ㅒ 가 같은 그림(획 정의 같음) → ㅔ 는 «ㅓ 글자 + 5열 세로획을 7열에 복사», 폭 9.
  glyph(ch) → (8×8 0/1 행렬, 글자 폭)
"""
import sys
sys.path.insert(0, r'C:\claude\project\aww-kr-patch\tools')
import hangul8comp as hc

_SWAP = {5: 4, 7: 6}   # 중성 번호: ㅔ(5)→ㅓ(4), ㅖ(7)→ㅕ(6)


def glyph(ch):
    o = ord(ch) - 0xAC00
    if 0 <= o < 11172:
        cho, jung, jong = o // 588, (o // 28) % 21, o % 28
        if jung in _SWAP:
            g = [list(r) for r in hc.glyph8(chr(0xAC00 + cho * 588 + _SWAP[jung] * 28 + jong))]
            y = next(i for i in range(8) if g[i][5])   # 모음 세로획 = 5열 첫 연속 구간만(받침 획 제외)
            while y < 8 and g[y][5]:
                g[y][7] = 1; y += 1
            return g, 9
        return [list(r) for r in hc.glyph8(ch)], 8
    raise ValueError(ch)


def thin2x(g):
    """8×8 → 16×16 «가는 2배»: 점은 (2x,2y), 가로·세로 이웃 사이 (2x+1,2y)/(2x,2y+1) 잇기,
       대각 이웃은 가로·세로로 이어지지 않을 때만 가운데 (2x+1,2y+1) 잇기 — 획 굵기 1픽셀(원래 16×16 글꼴과 같은 굵기)"""
    o = [[0] * 16 for _ in range(16)]
    on = lambda y, x: 0 <= y < 8 and 0 <= x < 8 and g[y][x]
    for y in range(8):
        for x in range(8):
            if not g[y][x]: continue
            o[2 * y][2 * x] = 1
            if on(y, x + 1): o[2 * y][2 * x + 1] = 1
            if on(y + 1, x): o[2 * y + 1][2 * x] = 1
            if on(y + 1, x + 1) and not on(y, x + 1) and not on(y + 1, x): o[2 * y + 1][2 * x + 1] = 1
            if on(y + 1, x - 1) and not on(y, x - 1) and not on(y + 1, x): o[2 * y + 1][2 * x - 1] = 1
    return o
