# -*- coding: utf-8 -*-
"""BG 비트맵 좌표 격자 보기 — python tools/bggrid.py B0200 x0 y0 x1 y1 [배율] → work/probe/grid_<파일>.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bggfx
n = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); S = int(sys.argv[6]) if len(sys.argv) > 6 else 3
rgb, _ = bggfx.load(n)
im = Image.fromarray(rgb[y0:y1, x0:x1]).resize(((x1 - x0) * S, (y1 - y0) * S), Image.NEAREST); dr = ImageDraw.Draw(im)
for x in range(x0 - x0 % 10, x1, 10):
    if x >= x0: dr.line([((x - x0) * S, 0), ((x - x0) * S, 4)], fill=(255, 255, 0)); dr.text(((x - x0) * S + 1, 0), str(x), fill=(255, 255, 0))
for y in range(y0 - y0 % 10, y1, 10):
    if y >= y0: dr.line([(0, (y - y0) * S), (4, (y - y0) * S)], fill=(0, 255, 255)); dr.text((0, (y - y0) * S), str(y), fill=(0, 255, 255))
im.save(os.path.join(os.path.dirname(HERE), 'work', 'probe', 'grid_%s.png' % n)); print(im.size)
