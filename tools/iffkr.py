# -*- coding: utf-8 -*-
r"""메뉴 16×16 글꼴 /S1/IFF.Z 에 한글 음절을 미리 그려 넣기(2026-10-11, khook 의 F3 경로 짝).
  IFF.Z = 압축 없는 VDP1 4비트 스프라이트 묶음(두 장 같음, 29,632 B) — 장면마다 통째로 VRAM 에 올라감(텍스처 0x44C‥0x547).
  가나·히라가나 칸 0x4A4‥0x547: 16×16(128 B) 146칸 + 작은 가나 8×16(64 B) 18칸(0x4D2‥0x4DA · 0x524‥0x52C), 파일 안 순서대로(0x4A4 = 0x2640).
  음절 번호 k(khook.table 정렬 순서) → 텍스처 tex16(k) = 0x4A4+k (0x4D2 이상이면 +9, 다시 0x524 이상이면 +9) — khook remap 과 같은 식.
  글꼴: 갈무리11(SIL OFL) 12px, 잉크 맨 위 줄 = 3(원래 가나와 같음), 왼쪽 1px 띄움, 화소 값 1.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FONT = (r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf', 12)
T0 = 0x4A4; OFF0 = 0x2640
SMALL = set(range(0x4D2, 0x4DB)) | set(range(0x524, 0x52D))
ADV16 = 12                                  # F3 폭 표(0x06083154)에 넣는 한글 간격


def tex16(k):
    t = T0 + k
    if t >= 0x4D2: t += 9
    if t >= 0x524: t += 9
    return t


def off(t):
    o = OFF0
    for u in range(T0, t): o += 64 if u in SMALL else 128
    return o


def glyph16(ch, font=None):
    from PIL import Image, ImageDraw, ImageFont
    fn = font or ImageFont.truetype(*FONT)
    ref = Image.new('1', (24, 24)); d = ImageDraw.Draw(ref); d.fontmode = '1'; d.text((0, 0), '한', font=fn, fill=1); top = ref.getbbox()[1]
    im = Image.new('1', (16, 16), 0); d = ImageDraw.Draw(im); d.fontmode = '1'; d.text((1, 3 - top), ch, font=fn, fill=1)
    return [[im.getpixel((x, y)) for x in range(16)] for y in range(16)]


def pack4(g):
    return bytes((g[y][x] << 4 | g[y][x + 1]) for y in range(16) for x in range(0, 16, 2))


def build(iff, syl):
    from PIL import ImageFont
    assert len(syl) <= 146, len(syl)
    fn = ImageFont.truetype(*FONT); d = bytearray(iff)
    for k, c in enumerate(syl):
        t = tex16(k); assert t not in SMALL and t <= 0x547
        o = off(t); d[o:o + 128] = pack4(glyph16(c, fn))
    return bytes(d)
