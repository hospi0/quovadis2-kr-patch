# -*- coding: utf-8 -*-
"""알려진 문장의 «같은 글자 반복 무늬»로 이진 자료에서 글자 코드 찾기 — find(data, text, width=1|2, step=1)"""


def sig(text):
    first = {}; return [first.setdefault(c, i) for i, c in enumerate(text)]


def find(data, text, width=2, endian='big', align=1, limit=20):
    n = len(text); sg = sig(text); out = []
    for st in range(0, len(data) - n * width, align):
        codes = [int.from_bytes(data[st + i * width:st + (i + 1) * width], endian) for i in range(n)]
        ok = True; seen = {}
        for i, c in enumerate(codes):
            j = sg[i]
            if j == i:
                if c in seen: ok = False; break
                seen[c] = i
            elif codes[j] != c: ok = False; break
        if ok and len(set(codes)) > n // 2:
            out.append((st, codes))
            if len(out) >= limit: break
    return out
