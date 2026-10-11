# -*- coding: utf-8 -*-
r"""메뉴·시스템 그림 글자 한글로(2026-10-11) — work/text/ui_ko.tsv(하스피 번역) · id = <.Z 이름>_<항목>.
  원본: 바탕 0 + 글자색(가장 많은 색) + 옅은 보조색. 글자 줄(가로 띠)마다 «덩어리»(가로 틈 ≥ 9px)로 나눔.
  번역: 줄 = «\n», 덩어리 = 전각 공백/두 칸 이상 공백. 짝지은 덩어리만 지우고 그 자리에 다시 그림(짝 없는 원본 덩어리 = 점선 등은 그대로).
  글꼴: 갈무리14/11/11좁은/9/7 중 띠 높이·자리 폭에 맞는 가장 큰 것. 가운데 정렬된 원본은 가운데로.
  긴 설명(행성 설명 PLAINF01_19‥27): 문단 «\n» 기준으로 폭에 맞춰 다시 접고 원본 줄 간격으로.
  build(장) → {'/S1/HUNI.Z': 바이트, …} · python tools/uigfx.py → work/probe/ui_kr.png
"""
import collections, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, zspr

TTC = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri.ttc'
FACES = [(0, 15), (1, 12), (3, 12), (4, 10), (5, 8)]          # (ttc 번호, 크기): 갈무리14·11·11좁은·9·7
_FONTS = [ImageFont.truetype(TTC, s, index=i) for i, s in FACES]
WRAP = {'PLAINF01_%d' % k for k in range(19, 28)}
_JS = lambda s: s.replace('전사자', '전사')                              # 4글자에 맞춤(하스피 «아군전사»)
LEFT = {'MDB_21': _JS, 'MDB_22': _JS}
NOCENTER = {'HUNI_32', 'MDB_31'}                                                 # 시스템 메뉴 «옵션»: 세이브·로드처럼 왼쪽(하스피 «줄맞춤»)
RALIGN0 = {'HUNI_23'}                                                  # «사용가능　　기»: 첫 덩어리는 원래 끝(숫자 앞)에 오른쪽 맞춤 — 숫자와 겹침 방지
FONTK = {'MDB_16': 1, 'HUNI_24': 1}                                    # 글꼴 고정(갈무리11): 결과 «시스템»은 갈무리14 가 골라져 위 잘림 · 배치 «시스템»은 원본 띠가 한 줄 낮아 갈무리9 로 작아짐(하스피 «굳이 작을 필요 없음») — 둘 다 옆 메뉴와 같게


def ink(font, s):
    im = Image.new('L', (len(s) * 20 + 20, 40), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
    d.text((2, 10), s, font=font, fill=1); a = np.array(im)
    ys = np.where(a.any(1))[0]; xs = np.where(a.any(0))[0]
    if not len(ys): return 0, 0, 0
    return xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1, ys[0] - 10


def xoff(font, s):
    im = Image.new('L', (len(s) * 20 + 20, 40), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
    d.text((2, 10), s, font=font, fill=1); xs = np.where(np.array(im).any(0))[0]
    return (xs[0] - 2) if len(xs) else 0


def runs(v, gap):
    out = []; s = None; last = None
    for i, x in enumerate(v):
        if x:
            if s is None: s = i
            elif i - last > gap: out.append((s, last + 1)); s = i
            last = i
    if s is not None: out.append((s, last + 1))
    return out


def analyse(p):
    m = p != 0
    bands = runs(m.any(1), 3)
    rows = []
    for y0, y1 in bands:
        segs = runs(m[y0:y1].any(0), 9)
        rows.append((y0, y1, segs))
    return rows


def pick1(s, hmax, wmax):
    for k, f in enumerate(_FONTS):
        w, h, _ = ink(f, s)
        if h <= hmax + 1 and w <= wmax: return k
    return len(_FONTS) - 1


def pick(s, hmax, wmax):
    return _FONTS[pick1(s, hmax, wmax)]


def fit(s, hmax, wmax, iid=None):
    """띄어쓰기 때문에 글꼴이 작아지면 붙여 씀(하스피 2026-10-11 «다 붙여서») → (글, 글꼴)"""
    if iid in FONTK: return s, _FONTS[FONTK[iid]]
    k = pick1(s, hmax, wmax)
    if ' ' in s and wmax <= 64:                                      # 작은 칸(메뉴 낱말)만
        s2 = s.replace(' ', ''); k2 = pick1(s2, hmax, wmax)
        if k2 < k: return s2, _FONTS[k2]
    return s, _FONTS[k]


def draw(p, fill, x, ytop, ybot, s, font, center_w=None):
    w, h, off = ink(font, s)
    im = Image.new('L', (p.shape[1] + 40, p.shape[0] + 40), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
    if center_w is not None: x = x + (center_w - w) // 2 - xoff(font, s)   # 잉크 왼쪽 끝 기준으로 가운데
    y = ytop + ((ybot - ytop) - h) // 2 - off
    y = min(max(y, -off), p.shape[0] - h - off)                       # 잉크가 그림 위·아래 밖으로 나가 잘리지 않게(MDB_16 «시스템» 템 윗줄 잘림)
    d.text((x + 20, y + 20), s, font=font, fill=1)
    a = np.array(im)[20:20 + p.shape[0], 20:20 + p.shape[1]]
    p[a > 0] = fill


KEEPVAL = {'HUNI_18': (8, 21, 91)}                                     # 빗금 무늬(값 8)는 글자 아님 — 빗금 사이(열 21‥90)만 다시 그림


def redraw(p, ko, iid):
    if iid in KEEPVAL:
        v, c0, c1 = KEEPVAL[iid]; q = p.copy()
        sub = q[:, c0:c1].copy(); sub[sub == v] = 0
        q[:, c0:c1] = np.where(p[:, c0:c1] == v, v, redraw(sub, ko, iid + '#')); return q
    iid = iid.rstrip('#')
    p = p.copy(); m = p != 0
    fill = collections.Counter(p[m].tolist()).most_common(1)[0][0]
    rows = analyse(p); H, W = p.shape
    lines = ko.split('\\n')
    while len(lines) > 1 and not lines[-1].strip(): lines.pop()           # 끝 빈 줄(번역 끝 \n) 버림
    if iid in WRAP:
        pitch = int(np.median([rows[k + 1][0] - rows[k][0] for k in range(len(rows) - 1)])) if len(rows) > 1 else 16
        x0 = min(s[0][0] for _, _, s in rows); p[:] = 0
        f = _FONTS[1]; out = []
        for para in lines:
            cur = ''
            toks = []                                                  # 부호 뒤에서도 끊을 수 있게(부호 뒤 공백을 지웠으므로)
            for k, w in enumerate(para.split(' ')):
                for j, piece in enumerate(re.findall(r'[^,.!?…]*[,.!?…]+|[^,.!?…]+', w)):
                    toks.append((piece, k > 0 and j == 0))
            for wd, sp in toks:
                t = (cur + (' ' if sp else '') + wd) if cur else wd
                if ink(f, t)[0] <= W - x0 - 2: cur = t; continue
                if cur: out.append(cur)
                cur = wd
            out.append(cur)
        y = rows[0][0]
        assert y + pitch * (len(out) - 1) + 12 <= H, (iid, '넘침', len(out))
        for s in out:
            draw(p, fill, x0, y, y + 12, s, f); y += pitch
        return p
    if len(lines) != len(rows):                                        # 줄 수 다르면 높이를 똑같이 나눔
        p[:] = 0; hh = H // len(lines)
        for k, s in enumerate(lines):
            s, f = fit(s, hh - 2, W - 2); draw(p, fill, 0, k * hh, (k + 1) * hh, s, f, center_w=W)
        return p
    if iid in LEFT:                                                    # 전적 표: 붙여 쓰고 왼쪽 맞춤, 점선 앞까지 크게(하스피)
        lines = [LEFT[iid](s.replace(' ', '')) for s in lines]
        x0 = min(s[0][0] for _, _, s in rows if s)
        for (y0, y1, segs), t in zip(rows, lines):
            inkc = (p[y0:y1] != 0).any(0); low = inkc & ~(p[y0:max(y0, y1 - 3)] != 0).any(0)
            lead = [a for a, b in runs(low, 4) if b - a >= 12]
            right = (lead[0] - 2) if lead else W - 1
            p[y0:y1, :right + 1] = 0
            f = pick(t, y1 - y0, right - x0); draw(p, fill, x0 - xoff(f, t), y0, y1, t, f)
        return p
    allc = all(len(s) == 1 and abs(s[0][0] - (W - s[0][1])) <= 4 for _, _, s in rows) and iid not in NOCENTER
    for (y0, y1, segs), line in zip(rows, lines):
        tsegs = [t for t in re.split(r'　+|  +', line.strip()) if t]
        # 점선(잉크가 띠 아래 3줄 안에만 있는 열)은 글자 덩어리에서 빼고 그대로 둠
        inkc = (p[y0:y1] != 0).any(0); low = inkc & ~(p[y0:max(y0, y1 - 3)] != 0).any(0)
        body = inkc.copy()
        for a, b in runs(low, 4):                                      # 아래쪽만 찍힌 열이 12px 넘게 이어지면 점선
            if b - a >= 12: body[a:b] = False
        segs2 = []
        for sx0, sx1 in segs:
            cols = np.where(body[sx0:sx1])[0]
            if len(cols): segs2.append((sx0 + cols[0], sx0 + cols[-1] + 1))
        segs = segs2
        if len(tsegs) < len(segs):                                     # 번역 덩어리가 적으면 남는 원본 덩어리를 마지막 짝에 합침
            segs = segs[:len(tsegs) - 1] + [(segs[len(tsegs) - 1][0], segs[-1][1])] if tsegs else segs
        center = allc and len(tsegs) == 1
        for j, t in enumerate(tsegs[:len(segs)]):
            sx0, sx1 = segs[j]
            p[y0:y1, sx0:sx1] = 0
            right = segs[j + 1][0] - 2 if j + 1 < len(segs) else W - 1
            lead = np.where((p[y0:y1, sx1:] != 0).any(0))[0]            # 오른쪽에 남은 점선이 있으면 그 앞까지
            if j + 1 >= len(segs) and len(lead): right = sx1 + lead[0] - 2
            if iid in RALIGN0 and j == 0:
                t, f = fit(t, y1 - y0, sx1 - 1); w_ = ink(f, t)[0]; draw(p, fill, sx1 - w_ - xoff(f, t), y0, y1, t, f)
            elif center:
                t, f = fit(t, y1 - y0, W, iid); draw(p, fill, 0, y0, y1, t, f, center_w=W)
            else:
                t, f = fit(t, y1 - y0 + (1 if iid.startswith("SL_") else 0), max(right - sx0, W - sx0 - 2 if j + 1 >= len(segs) and not len(lead) else 0), iid); draw(p, fill, sx0 + (1 if iid in NOCENTER else 0), y0, y1, t, f)
    return p


def pack(p, bpp):
    f = p.ravel()
    return bytes(f.tolist()) if bpp == 8 else bytes(((f[0::2] << 4) | f[1::2]).tolist())


def items():
    out = []
    for ln in open(os.path.join(ROOT, 'work', 'text', 'ui_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 2 and c[1]: out.append((c[0], c[1]))
    return out


def build(disk, log=print, preview=None):
    byfile = collections.defaultdict(list)
    for iid, ko in items():
        f, k = iid.rsplit('_', 1); byfile[f].append((int(k), ko, iid))
    out = {}; names = {n for n, l, s in disc.files(disk)}
    for f, lst in byfile.items():
        n = '/S1/%s.Z' % f
        if n not in names: continue
        d = bytearray(disc.read(n, disk)); es = zspr.entries(bytes(d))
        for k, ko, iid in lst:
            e = es[k]; p = zspr.pixels(bytes(d), e); q = redraw(p, ko, iid)
            b = pack(q, e['bpp']); o = 0x1000 + e['off']; assert len(b) == e['size']; d[o:o + len(b)] = b
            # 같은 자리(오프셋)를 쓰는 다른 항목은 자동으로 같이 바뀜
            if preview is not None: preview.append((iid, p, q))
        out[n] = bytes(d)
    log('메뉴 그림(장 %d): 파일 %d · 항목 %d' % (disk, len(out), sum(len(v) for f, v in byfile.items() if '/S1/%s.Z' % f in names)))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    prev = []; build(1, preview=prev)
    pal = np.array([(0, 0, 40)] + [(255, 255, 255)] * 15, np.uint8)
    ims = []
    for iid, a, b in prev:
        A = Image.fromarray(pal[a]); B = Image.fromarray(pal[b])
        im = Image.new('RGB', (A.width * 2 + 6, A.height), (90, 90, 90)); im.paste(A, (0, 0)); im.paste(B, (A.width + 6, 0))
        ims.append(im.resize((im.width * 2, im.height * 2), Image.NEAREST))
    W = max(i.width for i in ims); cols = 2
    rows = [ims[k:k + cols] for k in range(0, len(ims), cols)]
    H = sum(max(i.height for i in r) + 6 for r in rows)
    sheet = Image.new('RGB', (W * cols + 10, H), (40, 40, 40)); y = 0
    for r in rows:
        x = 0
        for i in r: sheet.paste(i, (x, y)); x += W + 10
        y += max(i.height for i in r) + 6
    sheet.save(os.path.join(ROOT, 'work', 'probe', 'ui_kr.png')); print('미리보기', sheet.size)


if __name__ == '__main__':
    main()
