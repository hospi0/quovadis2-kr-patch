# -*- coding: utf-8 -*-
r"""VDP2 배경 비트맵 글자(2026-10-11) — BG/B0xxx.BIN = RGB555 빅엔디언 512×256(256 KB) 또는 1024×256(512 KB), 두 장 같은 내용.
  글자 지우기: 상자 안에서 «글자 화소»(판정 함수)를 고르고 1px 넓혀 cv2.inpaint 로 메움 → 그 자리에 한글.
  글자 색: 원문 글자 화소의 줄별 평균(세로 그러데이션 유지) · 테두리/그림자는 원문에서 고른 색.
  작업 표 JOBS: (파일들, (x0, y0, x1, y1) 지울 상자, 번역 id, 설정)
  build(장) → {'/BG/B0731.BIN': 바이트, …} · python tools/bggfx.py [파일…] → work/probe/bg_kr_<파일>.png(원본/한글 3배)
"""
import os, re, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

FD = r'C:\claude\utils\font\Galmuri-v2.40.3'
FONTS = {'g11': (os.path.join(FD, 'Galmuri11.ttf'), 12), 'g11b': (os.path.join(FD, 'Galmuri11-Bold.ttf'), 12),
         'g14': (os.path.join(FD, 'Galmuri14.ttf'), 15), 'g9': (os.path.join(FD, 'Galmuri9.ttf'), 10),
         'g11c': (os.path.join(FD, 'Galmuri11-Condensed.ttf'), 12)}
NB = r'C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf'
NR = r'C:/claude/utils/font/nanum-gothic/NanumGothic.ttf'
BIGF = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) +(?=\S)')


def bright(px):           # 밝은 글자(흰·연보라)
    return px.min(axis=2) >= 100


def white(px):            # 흰 글자만(탭·띠 밝은 가장자리 안 잡게 2026-10-11)
    return px.min(axis=2) >= 170


def light(px):            # 위→아래로 흐려지는 흰 글자(목록 열 이름 — 아래쪽 a0a0d0 까지)
    return px.min(axis=2) >= 140


def lav(px):              # 분홍 띠 위 연보라·흰 글자
    return (px[..., 1] >= 170) & (px[..., 2] >= 170)


def lavAA(px):            # 분홍 띠 위 글자 + 가장자리 섞인 화소(띠 몸통 G≈96)
    return (px[..., 1] >= 120) & (px[..., 2] >= 150)


def red(px):              # 빨간 글자(경고·디스크 교체 머리글)
    return (px[..., 0] >= 170) & (px[..., 1] < 90) & (px[..., 2] < 90)


def darkOnGreen(px):      # 초록 띠 위 어두운 글자
    return px[..., 1] < 140


def lightG(px):           # 분홍·보라 띠 위 밝은 글자 — G 가 높음
    return px[..., 1] >= 120


# (파일들, 지울 상자, id, 설정) — 설정: font · align('c'/'l') · pick(글자 판정) · box(그릴 자리, 없으면 지울 상자)
JOBS = [
    (('B0731',), (227, 7, 276, 19), 'BG_0731', dict(font='g11', pick=lavAA, colpick=lav, fill='col', aa=(NB, 11), box=(226, 7, 278, 18))),   # 글자 G≥170(띠 왼쪽 밝은 분홍은 G≈144)
    (('B0732',), (238, 7, 285, 19), 'BG_0731', dict(font='g11', pick=lavAA, colpick=lav, fill='col', aa=(NB, 11), box=(237, 7, 287, 18))),
]
JOBS += [
    (('B0720',), (10, 4, 70, 22), 'BG_0720', dict(font='g14', pick=darkOnGreen, fill='col', aa=(NB, 15), box=(9, 5, 69, 20), restore=[(0, 21, 110, 23)])),
    (('B0110',), (127, 16, 192, 34), 'BG_0110_1', dict(font='g14', pick=lightG, aa=(NB, 16), box=(112, 16, 206, 34))),
    (('B0110',), (50, 78, 79, 89), 'BG_0110_2', dict(font='g11', pick=light, fill='row', box=(48, 78, 81, 89))),      # 빨간 띠 위 — 줄 메우기(하스피 «얼룩·뭉개짐»)
    (('B0110',), (103, 78, 130, 89), 'BG_0110_3', dict(font='g11', pick=light, fill='row', box=(101, 78, 132, 89))),
    (('B0110',), (144, 78, 188, 89), 'BG_0110_4', dict(font='g11', pick=light, fill='row', box=(142, 78, 190, 89))),
    (('B0110',), (211, 78, 255, 89), 'BG_0110_5', dict(font='g11c', pick=light, fill='row', box=(209, 78, 257, 89))),
    (('B0110',), (250, 86, 304, 99), 'BG_0110_6', dict(font='g9', pick=bright, align='r', box=(240, 86, 304, 99))),
    (('B0110',), (232, 198, 305, 212), 'BG_0110_7', dict(font='g9', pick=bright, align='r', box=(220, 198, 305, 212))),
]
def dark(px): return px.max(axis=2) < 90
def magenta(px): return (px[..., 1] < 110) & (px[..., 0] >= 110)
def pink(px): return (px[..., 0] >= 140) & (px[..., 1] < 150) & (px[..., 2] >= 60) & (px[..., 0] > px[..., 1] + 40)
def whiteOrBlack(px): return (px.min(axis=2) >= 200) | (px.max(axis=2) < 40)
def intro(px): return (px.min(axis=2) >= 170) | pink(px)


_L = dict(font='g11', pick=white, align='l')
JOBS += [
    # 디브리핑 결과(B0800·B0810) — 숫자 뒤 단위 «기 격파» 등은 왼쪽 맞춤
    (('B0800',), (198, 46, 240, 62), 'BG_0800_1', dict(_L, box=(200, 46, 250, 62), base=True)),
    (('B0800',), (198, 61, 240, 77), 'BG_0800_2', dict(_L, box=(200, 61, 250, 77), base=True)),
    (('B0800',), (198, 76, 240, 92), 'BG_0800_3', dict(_L, box=(200, 76, 250, 92), base=True)),
    (('B0810',), (208, 84, 250, 100), 'BG_0800_1', dict(_L, box=(210, 84, 260, 100), base=True)),
    (('B0810',), (208, 99, 250, 115), 'BG_0800_2', dict(_L, box=(210, 99, 260, 115), base=True)),
    (('B0810',), (208, 114, 250, 130), 'BG_0800_3', dict(_L, box=(210, 114, 260, 130), base=True)),
    (('B0800',), (5, 108, 33, 124), 'BG_0800_4', dict(_L, box=(7, 108, 40, 124), base=True)),
    (('B0800',), (51, 108, 67, 124), 'BG_0800_5', dict(_L, box=(51, 108, 80, 124), base=True)),
    (('B0800',), (59, 126, 111, 146), 'BG_0800_6', dict(_L, box=(61, 128, 120, 144), base=True)),
    (('B0800',), (131, 126, 147, 146), 'BG_0800_7', dict(_L, box=(133, 128, 150, 144), base=True)),
    (('B0800',), (59, 147, 111, 167), 'BG_0800_8', dict(_L, box=(61, 149, 114, 166), base=True)),
    (('B0800',), (59, 167, 111, 187), 'BG_0800_9', dict(_L, box=(61, 169, 114, 186), base=True)),
    (('B0800',), (113, 167, 142, 187), 'BG_0800_10', dict(_L, box=(115, 169, 145, 186), base=True)),
    (('B0800',), (162, 167, 178, 187), 'BG_0800_11', dict(_L, box=(164, 169, 180, 186), base=True)),
    (('B0800',), (185, 167, 213, 187), 'BG_0800_12', dict(_L, box=(187, 169, 215, 186), base=True)),
    (('B0800',), (241, 167, 258, 187), 'BG_0800_11', dict(_L, box=(243, 169, 260, 186), base=True)),
    (('B0800',), (59, 188, 111, 208), 'BG_0800_13', dict(_L, box=(61, 190, 120, 207), base=True)),
    (('B0800',), (130, 188, 149, 208), 'BG_0800_11', dict(_L, box=(133, 190, 150, 207), base=True)),
    # 병사 정보(B0750·B0820 왼쪽 판)
    (('B0750', 'B0820'), (8, 106, 37, 122), 'BG_0750_1', dict(_L, box=(9, 106, 40, 122))),
    (('B0750', 'B0820'), (8, 119, 37, 135), 'BG_0750_2', dict(_L, box=(9, 119, 40, 135))),
    (('B0750', 'B0820'), (8, 132, 37, 148), 'BG_0750_3', dict(_L, box=(9, 132, 40, 148))),
    (('B0750', 'B0820'), (8, 145, 37, 161), 'BG_0750_4', dict(_L, box=(9, 145, 40, 161))),
    (('B0750', 'B0820'), (8, 162, 48, 176), 'BG_0750_5', dict(_L, box=(9, 160, 65, 176), base=True)),
    (('B0750', 'B0820'), (8, 173, 48, 189), 'BG_0750_6', dict(_L, box=(9, 173, 65, 189), base=True)),
    (('B0750', 'B0820'), (67, 162, 83, 176), 'BG_0750_7', dict(_L, box=(69, 160, 84, 176), base=True)),
    (('B0750', 'B0820'), (67, 173, 83, 189), 'BG_0750_7', dict(_L, box=(69, 173, 84, 189), base=True)),
    # 병사 정보 오른쪽 판(B0820) — 밝은 판 위 흰 글자(어두운 테두리)
    (('B0820',), (167, 48, 203, 61), 'BG_0820_1', dict(_L, pick=white, fill='hint', box=(169, 48, 230, 61))),   # 밑줄 줄(61·81·96·111)은 안 건드림, 막대는 양옆 이어 메움(하스피 «밑줄 작살»)
    (('B0820',), (168, 70, 242, 81), 'BG_0820_2', dict(_L, pick=white, fill='hint', box=(170, 70, 262, 81))),
    (('B0820',), (266, 70, 282, 81), 'BG_0750_7', dict(_L, pick=white, fill='hint', box=(268, 70, 284, 81), base=True)),
    (('B0820',), (168, 85, 250, 96), 'BG_0820_3', dict(_L, pick=white, fill='hint', box=(170, 85, 262, 96))),
    (('B0820',), (168, 99, 223, 111), 'BG_0820_4', dict(_L, pick=white, fill='hint', box=(170, 99, 262, 111))),
    (('B0820',), (166, 143, 194, 159), 'BG_0750_1', dict(font='g11', pick=white, box=(164, 143, 198, 159))),
    (('B0820',), (202, 143, 230, 159), 'BG_0750_2', dict(font='g11', pick=white, box=(200, 143, 234, 159))),
    (('B0820',), (238, 143, 266, 159), 'BG_0750_3', dict(font='g11', pick=white, box=(236, 143, 270, 159))),
    (('B0820',), (274, 143, 302, 159), 'BG_0820_5', dict(font='g11', pick=white, box=(272, 143, 306, 159))),
    # 기체별 전적 순위(B0830)
    (('B0830',), (88, 1, 222, 25), 'BG_0830_1', dict(font='g14', pick=bright, fill='row', aa=(NB, 17), box=(88, 1, 221, 22))),
    (('B0830',), (11, 31, 39, 46), 'BG_0830_2', dict(_L, box=(13, 31, 45, 46))),
    (('B0830',), (30, 45, 58, 60), 'BG_0830_3', dict(font='g11', pick=white, box=(28, 45, 62, 60))),
    (('B0830',), (108, 45, 148, 60), 'BG_0830_4', dict(font='g11', pick=white, box=(104, 45, 152, 60))),
    (('B0830',), (193, 45, 246, 60), 'BG_0830_5', dict(font='g11', pick=white, box=(193, 45, 246, 60))),
    (('B0830',), (61, 58, 101, 74), 'BG_0830_6', dict(font='g11', pick=white, box=(58, 58, 104, 74))),
    (('B0830',), (138, 59, 203, 74), 'BG_0830_7', dict(font='g11', pick=white, box=(136, 58, 200, 74))),
    (('B0830',), (241, 58, 287, 74), 'BG_0830_8', dict(font='g11', pick=white, box=(236, 58, 292, 74))),
    # 보충 병사·보유 목록 머리글과 열 이름
    (('B0840',), (3, 34, 82, 38), 'BG_0840_1', dict(font='g11', pick=lambda px: px.min(axis=2) >= 45, fill='hint', erase=True)),   # 탭 밑 흐린 글자 아랫부분(4줄)만 비침 → 지움
    (('B0840',), (8, 12, 68, 32), 'BG_0840_1', dict(font='g14', pick=white, align='l', box=(10, 12, 90, 32), aa=(NB, 16))),
    (('B0850',), (8, 15, 64, 29), 'BG_0840_1', dict(font='g11', pick=lambda px: px.min(axis=2) >= 45, fill='hint', align='l', box=(10, 15, 70, 29))),   # 뒤에 흐린 «補充兵士» 탭(하스피)
    (('B0850',), (6, 33, 93, 53), 'BG_0850_1', dict(font='g14', pick=white, align='l', box=(8, 33, 100, 53), aa=(NB, 16))),
    (('B0860',), (6, 14, 93, 38), 'BG_0860_1', dict(font='g14', pick=white, align='l', box=(8, 15, 100, 37), aa=(NB, 16))),
    (('B0850',), (37, 69, 67, 85), 'BG_0850_2', dict(font='g11', pick=light, fill='row', box=(33, 71, 71, 82))),
    (('B0850',), (95, 69, 124, 85), 'BG_0850_3', dict(font='g11', pick=light, fill='row', box=(91, 71, 128, 82))),
    (('B0850',), (168, 69, 244, 85), 'BG_0850_4', dict(font='g11c', pick=light, fill='row', box=(160, 71, 252, 82))),
    (('B0850',), (259, 69, 289, 85), 'BG_0850_5', dict(font='g11', pick=light, fill='row', box=(255, 71, 293, 82))),
    (('B0860',), (63, 50, 93, 65), 'BG_0860_2', dict(font='g11', pick=light, fill='row', box=(60, 52, 96, 63))),
    (('B0860',), (143, 50, 168, 65), 'BG_0860_3', dict(font='g11', pick=light, fill='row', box=(140, 52, 171, 63))),
    (('B0860',), (172, 50, 196, 65), 'BG_0860_4', dict(font='g11', pick=light, fill='row', box=(171, 52, 198, 63))),
    (('B0860',), (199, 50, 221, 65), 'BG_0860_5', dict(font='g11', pick=light, fill='row', box=(198, 52, 222, 63))),
    (('B0860',), (223, 50, 247, 65), 'BG_0860_6', dict(font='g11', pick=light, fill='row', box=(222, 52, 248, 63))),
    (('B0860',), (290, 50, 316, 65), 'BG_0860_7', dict(font='g11', pick=light, fill='row', box=(287, 52, 318, 63))),
    # 인트로 글(B1001) — 메카 그림 위, 테두리 · 「붉은 전갈」·오반 레이 분홍
    (('B1001',), (18, 50, 300, 186), 'BG_1001', dict(font='g11', pick=intro, hlpick=pink, wrap=True, lh=15, align='l', grow=2,
                                                   box=(22, 48, 300, 188), outline=(16, 24, 40), aa=(NB, 13), hl=('「붉은 전갈」', '오반 레이'), hlcolor=(248, 80, 136))),
    # 조작 설명(B1002)
    (('B1002',), (60, 8, 255, 30), 'BG_1002_H', dict(font='g14', pick=magenta, aa=(NB, 16))),
    (('B1002',), (36, 51, 107, 64), 'BG_1002_1', dict(_L, pick=dark, strip=3, box=(37, 50, 107, 66))),      # LR· 테두리 글자는 원본 그대로
    (('B1002',), (233, 41, 309, 54), 'BG_1002_2', dict(_L, pick=dark, strip=2, box=(233, 40, 310, 56))),
    (('B1002',), (228, 68, 308, 83), 'BG_1002_3', dict(_L, pick=whiteOrBlack, color=(240, 240, 240), outline=(0, 0, 0), box=(229, 66, 309, 85))),
    (('B1002',), (12, 99, 99, 111), 'BG_1002_4', dict(_L, pick=dark, strip=2, box=(13, 98, 100, 113))),
    (('B1002',), (260, 158, 307, 174), 'BG_1002_5', dict(_L, pick=whiteOrBlack, color=(240, 240, 240), outline=(0, 0, 0), box=(261, 156, 308, 176))),
    (('B1002',), (249, 189, 306, 202), 'BG_1002_6', dict(_L, pick=dark, strip=2, box=(250, 187, 307, 204))),
    (('B1002',), (12, 185, 93, 212), 'BG_1002_7', dict(_L, pick=dark, lh=13, box=(13, 185, 93, 212))),
    (('B1002',), (110, 185, 211, 212), 'BG_1002_8', dict(_L, pick=dark, lh=13, box=(111, 185, 211, 212))),
    # 1장 끝 예고(B1003)
    (('B1003',), (40, 12, 295, 50), 'BG_1003_1', dict(font='g11', pick=white, lh=16, align='l', box=(45, 12, 300, 50), aa=(NR, 13))),
    (('B1003',), (28, 185, 295, 211), 'BG_1003_2', dict(font='g14', pick=white, box=(28, 185, 295, 211), aa=(NR, 18))),
]
# 경고·디스크 교체 창(B0200‥B020A) — 윗상자(가운데 정렬 흰 글자) · 아랫상자 · 머리글(빨강)
_WARN = {'B0200': ((87, 75, 231, 115), (40, 133, 277, 207)), 'B0201': ((100, 75, 218, 115), (41, 141, 278, 199)),
         'B0202': ((87, 84, 240, 110), (17, 141, 300, 199)), 'B0203': ((76, 75, 242, 115), (16, 133, 302, 207)),
         'B0204': ((67, 88, 256, 98), (79, 152, 239, 179)), 'B0205': ((88, 81, 230, 107), (22, 141, 300, 199)),
         'B0206': ((89, 81, 231, 107), (85, 152, 233, 179)), 'B0207': ((35, 72, 283, 114), (42, 133, 277, 207)),
         'B0208': ((35, 72, 283, 114), (42, 133, 277, 207)), 'B0209': ((61, 75, 267, 115), (32, 133, 286, 207)),
         'B020A': ((78, 75, 242, 115), (18, 141, 301, 199))}
for _n, (_u, _l) in _WARN.items():
    _k = 'BG_' + _n[1:]
    JOBS.append(((_n,), (_u[0] - 2, _u[1] - 2, _u[2] + 3, _u[3] + 3), _k + '_1', dict(font='g11', pick=white, lh=14, box=(30, _u[1] - 4, 290, _u[3] + 5))))
    JOBS.append(((_n,), (_l[0] - 2, _l[1] - 2, _l[2] + 3, _l[3] + 3), _k + '_2', dict(font='g11', pick=white, lh=15, box=(10, _l[1] - 6, 310, _l[3] + 7))))
    if _n in ('B0207', 'B0208'):
        JOBS.append(((_n,), (28, 42, 292, 65), 'BG_0207_H', dict(font='g14', pick=red, color=(255, 0, 0), aa=(NB, 18))))
    else:
        JOBS.append(((_n,), (76, 30, 122, 76), 'BG_02XX_H', dict(font='g14', pick=red, color=(255, 0, 0), aa=(BIGF, 42), text=0)))
        JOBS.append(((_n,), (197, 30, 243, 76), 'BG_02XX_H', dict(font='g14', pick=red, color=(255, 0, 0), aa=(BIGF, 42), text=1)))


def load(name, disk=1):
    d = disc.read('/BG/%s.BIN' % name, disk)
    W = 512 if len(d) == 262144 else 1024
    a = np.frombuffer(d, '>u2').reshape(-1, W)
    return np.dstack([(a & 31) << 3, ((a >> 5) & 31) << 3, ((a >> 10) & 31) << 3]).astype(np.uint8), a


def pack(rgb, a0):
    r, g, b = [(rgb[..., k].astype(np.uint16) >> 3) for k in range(3)]
    a = (a0 & 0x8000) | (b << 10) | (g << 5) | r
    return a.astype('>u2').tobytes()


def tr():
    out = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'gfx2_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 2: out[c[0]] = '\n'.join(PUNCT_SP.sub(r'\1', p) for p in c[1].split('\\n'))
    return out


def wrap(text, f, W):
    """문단(\n)마다 띄어쓰기 단위로 폭 W 안에 접기"""
    dr = ImageDraw.Draw(Image.new('1', (8, 8))); out = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split(' '):
            t = (cur + ' ' + w) if cur else w
            if dr.textlength(t, font=f) <= W: cur = t
            else: out.append(cur); cur = w
        out.append(cur)
    return '\n'.join(out)


def text_mask(text, font, w, h, align, scale=1, lh=None, hl=(), wrapit=False):
    """→ (글자 마스크, 강조 마스크)"""
    f = ImageFont.truetype(*FONTS[font])
    W, H = -(-w // scale), -(-h // scale)
    if wrapit: text = wrap(text, f, W)
    im = Image.new('1', (W, H), 0); dr = ImageDraw.Draw(im)
    hm = Image.new('1', (W, H), 0); hd = ImageDraw.Draw(hm)
    lines = text.split('\n'); lh = lh or FONTS[font][1] + 2
    ys = (H - lh * len(lines)) // 2 - 1
    assert ys >= -2 or len(lines) == 1, ('줄 수 넘침', text[:20], len(lines))
    for i, ln in enumerate(lines):
        l, t, r, b = dr.textbbox((0, 0), ln, font=f)
        assert r - l <= W, ('줄 넘침', ln, r - l, W)
        x = (W - (r - l)) // 2 - l if align == 'c' else (W - (r - l)) - l if align == 'r' else -l
        dr.text((x, ys + i * lh), ln, font=f, fill=1)
        for sub in hl:
            k = ln.find(sub)
            while k >= 0:
                hd.text((x + dr.textlength(ln[:k], font=f), ys + i * lh), sub, font=f, fill=1); k = ln.find(sub, k + 1)
    m = np.array(im, bool); hmk = np.array(hm, bool) & m
    if len(lines) == 1:                                                 # 한 줄은 잉크 기준 세로 가운데(넉넉한 판에 그려 위가 안 잘리게)
        big = Image.new('1', (W, H + 40), 0); bd = ImageDraw.Draw(big)
        l, t, r, b = bd.textbbox((0, 0), text, font=f)
        bd.text(((W - (r - l)) // 2 - l if align == 'c' else (W - (r - l)) - l if align == 'r' else -l, 20), text, font=f, fill=1)
        g = np.array(big, bool); ys_ = np.nonzero(g.any(axis=1))[0]
        g = g[ys_.min():ys_.max() + 1]; assert g.shape[0] <= H, ('줄 높이 넘침', text)
        m = np.zeros((H, W), bool); y = (H - g.shape[0]) // 2; m[y:y + g.shape[0]] = g; hmk = np.zeros_like(m)
    if scale > 1:
        m = np.kron(m, np.ones((scale, scale), bool))[:h, :w]; hmk = np.kron(hmk, np.ones((scale, scale), bool))[:h, :w]
    return m, hmk


def apply(rgb, box, text, cfg):
    x0, y0, x1, y1 = box; sub = rgb[y0:y1, x0:x1].copy()
    old = cfg['pick'](sub)
    assert old.any(), ('글자 화소 없음', box)
    base = old & ~(cfg['hlpick'](sub) if cfg.get('hlpick') else np.zeros_like(old))
    if cfg.get('colpick'): base = cfg['colpick'](sub)                    # 글자색은 진한 글자 화소에서만
    rows = np.array([sub[r][base[r]].mean(axis=0) if base[r].any() else [0, 0, 0] for r in range(sub.shape[0])])
    have = base.any(axis=1); idx = np.nonzero(have)[0]
    for r in range(len(rows)):
        if not have[r]: rows[r] = rows[idx[np.argmin(abs(idx - r))]]
    mk = cv2.dilate(old.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=cfg.get('grow', 1))
    if cfg.get('fill') == 'col':                                        # 가로 그러데이션 띠: 같은 세로줄의 글자 아닌 화소 평균으로(띠 가장자리 안 건드림)
        clean = sub.copy(); mb = mk.astype(bool)
        for c in range(sub.shape[1]):
            keep = ~mb[:, c]
            if keep.any(): clean[mb[:, c], c] = sub[keep, c].mean(axis=0)
            else: clean[mb[:, c], c] = clean[mb[:, c], c - 1] if c else sub[:, c].mean(axis=0)
    elif cfg.get('fill') == 'hint':                                     # 같은 가로줄 양옆 가장 가까운 글자 아닌 화소 사이를 이어 메움(막대 끝 모양 유지)
        clean = sub.copy(); mb = mk.astype(bool)
        for r in range(sub.shape[0]):
            keep = np.nonzero(~mb[r])[0]
            if not len(keep): continue
            for c in np.nonzero(mb[r])[0]:
                L = keep[keep < c]; R = keep[keep > c]
                if len(L) and len(R):
                    a_, b_ = L[-1], R[0]; w_ = (c - a_) / (b_ - a_)
                    clean[r, c] = (sub[r, a_] * (1 - w_) + sub[r, b_] * w_).astype(np.uint8)
                else: clean[r, c] = sub[r, L[-1] if len(L) else R[0]]
    elif cfg.get('fill') == 'row':                                      # 가로 줄무늬 띠: 같은 가로줄의 글자 아닌 화소 평균으로
        clean = sub.copy(); mb = mk.astype(bool)
        for r in range(sub.shape[0]):
            keep = ~mb[r]
            if keep.any(): clean[r, mb[r]] = sub[r, keep].mean(axis=0)
            else:                                                       # 줄 전체가 글자 → 상자 바로 바깥 좌우 화소로
                side = np.concatenate([rgb[y0 + r, max(x0 - 3, 0):x0], rgb[y0 + r, x1:x1 + 3]])
                clean[r, mb[r]] = side.mean(axis=0)
    else:
        clean = cv2.inpaint(np.ascontiguousarray(sub[..., ::-1]), mk, 3, cv2.INPAINT_TELEA)[..., ::-1]
    bx = cfg.get('box') or box
    if cfg.get('erase'):                                                # 지우기만(잘려서 번역할 수 없는 흐린 글자 조각)
        out = rgb.copy(); out[y0:y1, x0:x1] = clean; return out
    if cfg.get('aa'):                                                   # 큰 글자: 고해상도 글꼴 + 가장자리 섞기(2026-10-11 하스피 «경고 너무 저해상도»)
        path, size = cfg['aa']; f = ImageFont.truetype(path, size)
        bw, bh = bx[2] - bx[0], bx[3] - bx[1]; align = cfg.get('align', 'c')
        lines = text.split('\n'); dr0 = ImageDraw.Draw(Image.new('L', (8, 8)))
        if cfg.get('wrap'): lines = wrap(text, f, bw).split('\n')
        lh = cfg.get('lh') or size + 2
        L = Image.new('L', (bw, lh * len(lines) + size * 2), 0); dl = ImageDraw.Draw(L)
        Hh = Image.new('L', L.size, 0); dh = ImageDraw.Draw(Hh)
        for i, ln in enumerate(lines):
            tw = dr0.textlength(ln, font=f); assert tw <= bw + 0.5, ('줄 넘침', ln, tw, bw)
            x = (bw - tw) / 2 if align == 'c' else bw - tw if align == 'r' else 0
            dl.text((x, size // 2 + i * lh), ln, font=f, fill=255)
            for sub_ in cfg.get('hl', ()):
                k = ln.find(sub_)
                while k >= 0:
                    dh.text((x + dr0.textlength(ln[:k], font=f), size // 2 + i * lh), sub_, font=f, fill=255); k = ln.find(sub_, k + 1)
        a = np.array(L, np.float32) / 255; ha = np.array(Hh, np.float32) / 255
        ys = np.nonzero(a.max(axis=1) > 0)[0]; a = a[ys.min():ys.max() + 1]; ha = ha[ys.min():ys.max() + 1]
        assert a.shape[0] <= bh, ('큰 글자 높이 넘침', text, a.shape[0], bh)
        oy = bx[1] + (bh - a.shape[0]) // 2
        out = rgb.copy(); out[y0:y1, x0:x1] = clean
        reg = out[oy:oy + a.shape[0], bx[0]:bx[2]].astype(np.float32)
        if cfg.get('outline') is not None:
            oa = cv2.dilate(a, np.ones((3, 3), np.uint8))[..., None]
            reg = reg * (1 - oa) + np.array(cfg['outline'], np.float32) * oa
        if cfg.get('color') is not None: col = np.broadcast_to(np.array(cfg['color'], np.float32), reg.shape)
        else:
            col = np.zeros(reg.shape, np.float32)
            for r in range(a.shape[0]): col[r] = rows[min(max(oy + r - y0, 0), len(rows) - 1)]
        al = a[..., None]; reg = reg * (1 - al) + col * al
        if ha.any(): hb = ha[..., None]; reg = reg * (1 - hb) + np.array(cfg['hlcolor'], np.float32) * hb
        out[oy:oy + a.shape[0], bx[0]:bx[2]] = reg.round().clip(0, 255).astype(np.uint8)
        return out
    m, hmk = text_mask(text, cfg['font'], bx[2] - bx[0], bx[3] - bx[1], cfg.get('align', 'c'), cfg.get('scale', 1), cfg.get('lh'), cfg.get('hl', ()), cfg.get('wrap', False))
    if cfg.get('base'):                                                  # 원문 잉크 맨 아랫줄에 맞춤(숫자와 높이 — 하스피 2026-10-11 «격파수·~종 숫자랑 높이 안 맞음»)
        rr = np.nonzero(m.any(axis=1))[0]; d = (y0 + np.nonzero(old.any(axis=1))[0].max()) - (bx[1] + rr.max())
        top, bot = bx[1] + rr.min() + d, bx[1] + rr.max() + d                # 맞춘 잉크의 절대 위·아래
        ny0, ny1 = min(bx[1], top), max(bx[3], bot + 1)                      # 상자를 넘으면 그리는 상자를 넓힘(«기체개량» 원문이 상자 위로 걸침)
        m2 = np.zeros((ny1 - ny0, m.shape[1]), bool); m2[top - ny0:bot - ny0 + 1] = m[rr.min():rr.max() + 1]
        m, hmk = m2, np.zeros_like(m2); bx = (bx[0], ny0, bx[2], ny1)
    if cfg.get('color') is not None: rows[:] = cfg['color']
    out = rgb.copy(); out[y0:y1, x0:x1] = clean
    reg = out[bx[1]:bx[3], bx[0]:bx[2]]
    if cfg.get('shadow') is not None:
        sh = np.zeros_like(m); sh[1:, 1:] = m[:-1, :-1]; reg[sh & ~m] = cfg['shadow']
    if cfg.get('outline') is not None:
        ol = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool); reg[ol & ~m] = cfg['outline']
    for r in range(m.shape[0]):
        rr = min(max(r + bx[1] - y0, 0), len(rows) - 1)
        reg[r][m[r]] = rows[rr]
    if hmk.any(): reg[hmk] = cfg['hlcolor']
    return out


def render(name, disk, t):
    rgb, a0 = load(name, disk); orig = rgb.copy()
    for files, box, key, cfg in JOBS:
        if name in files:
            tx = t[key] if 'text' not in cfg else t[key][cfg['text']]
            tx = tx[cfg.get('strip', 0):]
            rgb = apply(rgb, box, tx, cfg)
            for rx0, ry0, rx1, ry1 in cfg.get('restore', ()): rgb[ry0:ry1, rx0:rx1] = orig[ry0:ry1, rx0:rx1]   # 국소: 원본 화소 그대로 되돌림
    return orig, rgb, a0


# .Z 안 16비트 RGB 스프라이트(깃발 0x08) — (파일, 항목 번호) → 작업들. 앞 단계(uigfx 등)가 고친 바이트 위에 덧씀(base)
SPR = {('/S1/HUNI.Z', 14): [((12, 8, 70, 22), 'HUNI_14', dict(font='g14', pick=lambda px: px[..., 0] >= 24, fill='col', aa=(NB, 13), align='l', box=(14, 8, 69, 22)))]}


def spr_rgb(d, i):
    import zspr
    e = zspr.entries(bytes(d))[i]; o = 0x1000 + e['off']
    a = np.frombuffer(bytes(d[o:o + e['w'] * e['h'] * 2]), '>u2').reshape(e['h'], e['w'])
    return o, a, np.dstack([(a & 31) << 3, ((a >> 5) & 31) << 3, ((a >> 10) & 31) << 3]).astype(np.uint8)


def build_spr(disk, base=None, log=print):
    t = tr(); out = {}
    for (n, i), jobs in SPR.items():
        d = bytearray((base or {}).get(n) or disc.read(n, disk))
        o, a0, rgb = spr_rgb(d, i)
        for box, key, cfg in jobs: rgb = apply(rgb, box, t[key], cfg)
        b = pack(rgb, a0); d[o:o + len(b)] = b; out[n] = bytes(d)
    log('RGB 스프라이트 글자(장 %d): %d' % (disk, sum(len(v) for v in SPR.values())))
    return out


def build(disk, log=print):
    t = tr(); out = {}
    for name in sorted({f for files, b, k, c in JOBS for f in files}):
        orig, rgb, a0 = render(name, disk, t)
        out['/BG/%s.BIN' % name] = pack(rgb, a0)
    log('배경 그림(장 %d): BG 파일 %d · 글자 %d' % (disk, len(out), sum(len(f) for f, b, k, c in JOBS)))
    return out


def preview(names):
    t = tr()
    for name in names:
        orig, rgb, a0 = render(name, 1, t)
        assert pack(orig, a0) == disc.read('/BG/%s.BIN' % name, 1), '왕복 실패'
        W = orig.shape[1] if orig.shape[1] == 512 else 512
        im = np.vstack([orig[:, :320], np.full((4, 320, 3), 255, np.uint8), rgb[:, :320]])
        Image.fromarray(im).resize((im.shape[1] * 3, im.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'probe', 'bg_kr_%s.png' % name))
        print(name)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    preview(sys.argv[1:] or sorted({f for files, b, k, c in JOBS for f in files}))
