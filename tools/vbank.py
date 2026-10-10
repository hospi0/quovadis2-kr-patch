# -*- coding: utf-8 -*-
r"""음성 묶음 V????.B(2026-10-11 조사) — 머리 16 B 칸 ×n: (00FF 0000, 값?, 시작, 길이), 0 칸에서 끝
  clips(데이터) → [(시작, 길이, 값)]"""
import struct


def clips(d):
    out = []
    for i in range(0, 0x100, 16):
        a, v, o, n = struct.unpack_from('>4I', d, i)
        if a != 0x00FF0000: break
        out.append((o, n, v))
    return out
