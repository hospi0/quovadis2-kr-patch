# -*- coding: utf-8 -*-
"""VDP1 명령표 걷기(스테이트 V1 빅엔디언) — cmds(V) → [(주소, 16워드)] (건너뛰기 칸 뺌, 호출/복귀 처리)"""
import struct


def cmds(V, start=0, limit=4000):
    out = []; a = start; stack = []; n = 0
    while n < limit:
        n += 1; w = struct.unpack_from('>16H', V, a)
        if w[0] & 0x8000: break
        jp = (w[0] >> 12) & 7
        if not jp & 4: out.append((a, w))
        m = jp & 3
        if m == 1: a = w[1] * 8
        elif m == 2: stack.append(a + 32); a = w[1] * 8
        elif m == 3 and stack: a = stack.pop()
        else: a += 32
    return out


def s16(v): return v - 0x10000 if v & 0x8000 else v


def sprite(w):
    """일반 스프라이트(0)/크기(1)/변형(2) → dict"""
    return dict(cmd=w[0] & 15, src=w[4] * 8, w=((w[5] >> 8) & 0x3F) * 8, h=w[5] & 0xFF, pmod=w[2], col=w[3], x=s16(w[6]), y=s16(w[7]), dir=(w[0] >> 4) & 3)
