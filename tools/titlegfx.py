# -*- coding: utf-8 -*-
r"""타이틀 화면 한글(2026-10-11) — /BG/B0001.BIN(RGB555 빅엔디언 512×256, 두 장 같음, 보이는 곳 320×224).
  원문 세 줄 «惑星強襲 / オヴァン・レイ / クォヴァディス2» → «혹성강습 / 오반·레이 / 쿼바디스 2»(하스피: 공식 표기 «쿼바디스»).
  지우기: 상자 안 글자 화소(붉은·분홍: R≥150 & R−G≥40) + 2px 넓힌 테두리 → cv2.inpaint(바탕 우주·사선 장식 쪽에서 메움).
  그리기: 굵은 고딕(가장자리 섞기) · 색 = 원문 글자 화소의 줄별 평균(위 밝은 분홍 → 아래 빨강) · 어두운 테두리 1px + 오른쪽 아래 그림자.
  build(장) → {'/BG/B0001.BIN': 바이트} · python tools/titlegfx.py → work/probe/title_kr.png(원본/한글 2배)
"""
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

FILE = '/BG/B0001.BIN'; W, H = 512, 256
FONT = r'C:\claude\utils\font\logo\BlackHanSans.ttf'
LIT0, LIT1 = 1.12, 0.68                                                     # 글자 왼쪽·오른쪽 밝기 배율
# (지울 상자 x0,y0,x1,y1 · 한글 · 글자 높이(잉크) · 가운데 x)
LINES = [((104, 74, 220, 106), '혹성강습', 27, 162, 0),
         ((72, 110, 242, 142), '오반·레이', 27, 'axis', 0),
         ((102, 148, 212, 164), '쿼바디스 2', 12, 'axis', 0)]          # 마지막 = 맞출 폭(0 = 그대로)


def load(d):
    a = np.frombuffer(d, '>u2').reshape(H, W).astype(np.int32)
    return np.stack([(a & 31), (a >> 5 & 31), (a >> 10 & 31)], -1) * 8 + 4


def save(rgb, d0):
    """★원본 화소의 최상위 비트(0x8000 = VDP2 RGB «보임») 그대로 — 버리면 타이틀이 통째로 투명(2026-10-11 실기 «타이틀화면 사라짐»)"""
    c = np.clip(np.rint(rgb), 0, 255).astype(np.int32) >> 3
    msb = np.frombuffer(d0, '>u2').reshape(H, W).astype(np.int32) & 0x8000
    return (msb | c[..., 0] | c[..., 1] << 5 | c[..., 2] << 10).astype('>u2').tobytes()


def textmask(rgb):
    """원문 글자 = 붉은 그러데이션(밝은 쪽 R≥150 · 어두운 오른쪽 가장자리 R 0x60‥ G 0x34‥) — 바탕 우주는 G≈0, 사선 장식은 R−G 작음"""
    R, G = rgb[..., 0], rgb[..., 1]
    return ((R >= 150) & (R - G >= 40)) | ((R >= 0x50) & (G >= 0x2C) & (R - G >= 0x20))


def colmask(rgb):                                                        # 글자색 평균은 밝은 몸통만
    R, G = rgb[..., 0], rgb[..., 1]
    return (R >= 150) & (R - G >= 40)


def render(text, height, width=None):
    """→ (알파 0‥1 배열) 잉크 높이 = height · width 주면 글자 사이를 고르게 벌려 그 폭에 맞춤 · «·» 는 글꼴에 없어 네모 점으로"""
    size = height
    for _ in range(40):
        f = ImageFont.truetype(FONT, size); im = Image.new('L', (size * 2, size * 3), 0)
        ImageDraw.Draw(im).text((size // 2, size // 2), '혹', font=f, fill=255)
        bb = im.getbbox()
        if bb[3] - bb[1] >= height: break
        size += 1
    top = bb[1]; glyphs = []
    for ch in text:
        if ch == ' ': glyphs.append(np.zeros((height, max(3, height // 4)), np.float32)); continue
        if ch == '·':
            d = max(3, height // 6); g = np.zeros((height, d + 2), np.float32); c = height // 2 - d // 2; g[c:c + d, 1:1 + d] = 1; glyphs.append(g); continue
        im = Image.new('L', (size * 2, size * 3), 0); ImageDraw.Draw(im).text((size // 2, size // 2), ch, font=f, fill=255)
        a = np.array(im).astype(np.float32) / 255; xs = np.where(a.any(0))[0]
        glyphs.append(a[top:top + height, xs[0]:xs[-1] + 1])
    ink = sum(g.shape[1] for g in glyphs); gap = max(1, round(((width or 0) - ink) / max(1, len(glyphs) - 1))) if width else max(1, height // 9)
    out = np.zeros((height, ink + gap * (len(glyphs) - 1)), np.float32); u = np.zeros(out.shape[1], np.float32); x = 0; spans = []
    for g in glyphs:
        out[:, x:x + g.shape[1]] = np.maximum(out[:, x:x + g.shape[1]], g); u[x:x + g.shape[1]] = np.linspace(0, 1, g.shape[1])
        spans.append((x, x + g.shape[1])); x += g.shape[1] + gap
    return out, u, spans                                                   # u = 글자 안 가로 위치 0(왼쪽)‥1(오른쪽) · spans = 글자별 (시작, 끝)


def build_img(rgb):
    out = rgb.astype(np.float32).copy()
    tm = textmask(rgb)
    for (x0, y0, x1, y1), ko, hgt, cx, wid in LINES:
        sub = tm[y0:y1, x0:x1]
        ys = np.where(sub.any(1))[0]
        cm = colmask(rgb)[y0:y1, x0:x1]
        # 빛 지도: 원문 글자의 가로 밝기(하스피 «혹·강 사이 밝은 띠» = 사선 장식 빛) → 부드럽게 번져 배율로
        lum = rgb[y0:y1, x0:x1].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
        cnt = cm.sum(0); prof = np.where(cnt > 0, (lum * cm).sum(0) / np.maximum(cnt, 1), np.nan)
        ok = ~np.isnan(prof); prof = np.interp(np.arange(len(prof)), np.where(ok)[0], prof[ok])
        prof = cv2.GaussianBlur(prof.astype(np.float32).reshape(1, -1), (0, 0), 4).ravel()
        base = np.median(prof); band = np.clip(prof / base, 0.75, 2.2)
        plain = band < 1.12                                               # 띠 없는 곳에서만 기본색
        rows = [rgb[y0 + y, x0:x1][cm[y] & plain].mean(0) if (cm[y] & plain).any() else rgb[y0 + y, x0:x1][sub[y]].mean(0) for y in ys]
        # 지우기
        m = np.zeros((H, W), np.uint8); m[y0:y1, x0:x1] = sub.astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((3, 3), np.uint8))
        out = cv2.inpaint(np.clip(out, 0, 255).astype(np.uint8), m, 4, cv2.INPAINT_TELEA).astype(np.float32)
        # 그리기
        al, u, spans = render(ko, hgt, wid or None); h, w = al.shape
        if cx == 'axis': cx = axis                                        # 윗줄 «성»과 «강» 사이에 가운데 맞춤(하스피)
        tx = int(round(cx - w / 2))
        if ko == '혹성강습': axis = tx + (spans[1][1] + spans[2][0]) / 2
        ty = y0 + int(ys[0]) + (int(ys[-1] - ys[0]) + 1 - h) // 2
        # 원문 줄별 평균은 반사광 띠로 계단짐(하스피 «그라데이션이 너무 딱딱») → 2차 곡선으로 매끈하게
        rs = np.array(rows, np.float32); t = np.linspace(0, 1, len(rs)); tt = np.linspace(0, 1, h)
        grad = np.stack([np.polyval(np.polyfit(t, rs[:, c], 2), tt) for c in range(3)], -1).astype(np.float32)
        a8 = (al * 255).astype(np.uint8)
        edge = cv2.dilate(a8, np.ones((3, 3), np.uint8)).astype(np.float32) / 255
        sh = np.zeros_like(edge); sh[1:, 1:] = edge[:-1, :-1]
        reg = out[ty:ty + h, tx:tx + w]
        dark = np.array([40, 0, 8], np.float32)
        for lay, col in ((sh, dark * 0.6), (edge, dark)):
            reg[:] = reg * (1 - lay[..., None]) + col * lay[..., None]
        lit = (LIT0 + (LIT1 - LIT0) * u)[None, :, None]                   # 원문처럼 글자마다 왼쪽 밝고 오른쪽 어둡게(«イ» R 0xAC→0x6C)
        bx = np.interp(np.arange(tx, tx + w), np.arange(x0, x1), band)[None, :, None]
        reg[:] = reg * (1 - al[..., None]) + np.clip(grad[:, None, :] * lit * bx, 0, 255) * al[..., None]
    return out


def build(disk, log=print):
    d0 = disc.read(FILE, disk); rgb = load(d0); b = save(build_img(rgb), d0)
    o = np.frombuffer(d0, '>u2'); n = np.frombuffer(b, '>u2')
    assert len(b) == len(d0) and ((o & 0x8000) == (n & 0x8000)).all(), '타이틀 MSB 깨짐'
    log('타이틀 그림(장 %d): %s' % (disk, FILE))
    return {FILE: b}


if __name__ == '__main__':
    rgb = load(disc.read(FILE, 1)); kr = build_img(rgb)
    a = np.clip(rgb[:224, :320], 0, 255).astype(np.uint8); b = np.clip(kr[:224, :320], 0, 255).astype(np.uint8)
    im = Image.fromarray(np.concatenate([a, b], 1)); im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'probe', 'title_kr.png'))
