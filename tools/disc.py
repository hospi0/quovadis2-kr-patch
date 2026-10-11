# -*- coding: utf-8 -*-
r"""쿠오바디스 2 트랙 1 ISO 읽기(2026-10-11, 건담 disc.py 꼴) — files(장) · read(이름, 장)"""
import importlib.util as _iu
_sp = _iu.spec_from_file_location('_gdisc', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\disc.py')
_g = _iu.module_from_spec(_sp); _sp.loader.exec_module(_g)
BIN = r'C:\claude\roms\ss\완료\QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc %d)\QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc %d) (Track 1).bin'
_cache = {}


def files(disk=1):
    if disk not in _cache: _cache[disk] = _g.files(BIN % (disk, disk))
    return _cache[disk]


def read(name, disk=1):
    for n, l, s in files(disk):
        if n == name:
            out = bytearray()
            with open(BIN % (disk, disk), 'rb') as f:
                for i in range((s + 2047) // 2048):
                    f.seek((l + i) * 2352 + 16); out += f.read(2048)
            return bytes(out[:s])
    raise KeyError(name)
