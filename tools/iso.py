# -*- coding: utf-8 -*-
r"""트랙 1 파일 제자리 바꿔 넣기(2026-10-11) — 같은 섹터 수 안에서만(크기 늘리기 없음). 섹터 머리·EDC/ECC 새로(유나 리믹스 iso.sector).
  patch(dst, 장, {'/0.BIN': bytes, ...})
"""
import importlib.util, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import disc

_sp = importlib.util.spec_from_file_location('yuna_iso', r'C:\claude\project\yunaremix-kr-patch\tools\iso.py')
_y = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_y)
sector = _y.sector


def patch(dst, disk, files, log=print):
    src = disc.BIN % (disk, disk)
    recs = {n: (l, s) for n, l, s in disc.files(disk)}
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, 'rb') as i, open(dst, 'wb') as o:
        while True:
            b = i.read(1 << 24)
            if not b: break
            o.write(b)
    with open(dst, 'r+b') as o:
        for name, data in files.items():
            lba, size = recs[name]
            assert len(data) == size, ('크기 다름', name, len(data), size)
            for k in range((size + 2047) // 2048):
                o.seek((lba + k) * 2352); o.write(sector(lba + k, data[k * 2048:(k + 1) * 2048].ljust(2048, b'\0')))
    with open(dst, 'rb') as f:                                         # 되읽기 검산
        for name, data in files.items():
            lba, size = recs[name]; out = bytearray()
            for k in range((size + 2047) // 2048):
                f.seek((lba + k) * 2352 + 16); out += f.read(2048)
            assert bytes(out[:size]) == data, name
    log('트랙 1(장 %d): 크기 그대로 · 바뀐 파일 %d' % (disk, len(files)))
