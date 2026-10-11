# -*- coding: utf-8 -*-
"""0.BIN SH-2 역어셈블 — python tools/sh2d.py 0x0604B640 [개수]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util as _iu
_sp = _iu.spec_from_file_location('_gdis', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2dis.py')
_g = _iu.module_from_spec(_sp); _sp.loader.exec_module(_g)
import disc
_b = None


def dis(addr, n=80):
    global _b
    if _b is None: _b = disc.read('/0.BIN', 1)
    return _g.dis(addr, n, _b, 0x06004000)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(dis(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 80)))
