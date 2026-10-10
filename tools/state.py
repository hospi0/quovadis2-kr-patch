# -*- coding: utf-8 -*-
r"""RetroArch(Beetle Saturn) 상태 → 메모리 덩어리(2026-10-11, 건담 state.py·which_voice.py 꼴)
  ram(상태) → {'H': WorkRAMH, 'L': WorkRAML, 'V1': VDP1 VRAM(u16 뒤집음 풀어 빅엔디언), 'SND': 사운드 RAM(빅엔디언)}
"""
import struct, sys
sys.path.insert(0, r'C:\claude\project\df2-kr-patch\tools')
import rzip, dump_state as ds


def ram(path):
    raw = open(path, 'rb').read()
    snap = rzip.unpack(path)[0] if raw[:5] == b'#RZIP' else raw
    out, used = {}, set()
    want = (('VRAM', 'V1'), ('VRAM', 'V2'), ('WorkRAML', 'L'), ('WorkRAMH', 'H'))
    hits = ds.find_vars(snap)
    for nm, tag in want:
        for k, (i, n, off, sz) in enumerate(hits):
            if n == nm and k not in used:
                used.add(k); out[tag] = ds.swap16(snap[off:off + sz]); break
    for i, n, off, sz in hits:
        if n == 'RAM' and sz == 524288:
            out['SND'] = ds.swap16(snap[off:off + sz])
    return out
