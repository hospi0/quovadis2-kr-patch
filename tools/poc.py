# -*- coding: utf-8 -*-
r"""자막 PoC(2026-10-11) — 미션대사2 대사(WDE00/VE001.B 조각 0) 한 개.
  python tools/poc.py            → 그림 미리보기 work/poc_sub.png + 흉내기 검산(스테이트 미션대사2 에서 훅 한 번)
  python tools/poc.py --write    → work/out/…(Disc 1) (Track 1).bin (0.BIN 만 제자리)
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, vbank, hook as H, state

FONT = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Condensed.ttf'
LINES = ['오반,화면 위 검은 차량이', '디온이야.지하도로 대통령이', '탈출할 때까지 시간을 벌어.']   # 부호 뒤 공백 없음(전프로젝트 규칙)
CLIP = ('/WDE00/VE001.B', 0)
STATE = os.path.join(ROOT, 'my files', '할일', '미션대사2.state3')
OUT = os.path.join(ROOT, 'work', 'out', 'QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc 1) (Track 1).bin')


def render(lines):
    """160×41 4비트: 0 투명 · 1 검정 테두리 · 2 흰 글자(갈무리11 좁은꼴 비트맵 그대로, 줄 간격 13, 가운데)"""
    w, h = H.W8 * 8, H.HT
    F = ImageFont.truetype(FONT, 12)
    g = np.zeros((h, w), bool)
    for i, t in enumerate(lines):
        im = Image.new('1', (w, 16), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
        tw = d.textlength(t, font=F); assert tw <= w - 2, (t, tw)
        d.text(((w - tw) // 2, 0), t, font=F, fill=1)
        a = np.array(im)[:13]; y = 1 + i * 13
        g[y:y + 13] |= a[:h - y]
    b = np.zeros_like(g)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            b |= np.roll(np.roll(g, dy, 0), dx, 1)
    px = np.where(g, 2, np.where(b, 1, 0)).astype(np.uint8)
    f = px.ravel()
    return bytes(((f[0::2] << 4) | f[1::2]).tolist()), px


def key():
    d = disc.read(CLIP[0]); o, ln, v = vbank.clips(d)[CLIP[1]]
    c = d[o:o + ln]
    return ln, struct.unpack_from('>I', c, H.keyoff(ln))[0]


def test(b, lab):
    import importlib.util
    sp = importlib.util.spec_from_file_location('sim', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2sim.py')
    S = importlib.util.module_from_spec(sp); sp.loader.exec_module(S)
    m0 = state.ram(STATE)
    def mk():
        m = S.Mem(); m.add(0x06000000, 0x100000, m0['H']); m.add(0x00200000, 0x100000, m0['L']); m.add(0x05C00000, 0x80000, m0['V1'])
        hb = m._f(H.AREA)[0]; hb[H.AREA - 0x06000000:H.AREA - 0x06000000 + len(b)] = b
        return m
    def walk(m, a):
        seen = set()
        while a not in seen:
            seen.add(a); c = m.r16(a)
            if c & 0x8000: return a, 'END'
            if c == 0x5000 and m.r16(a + 2) == H.OWNL: return a, 'OURS'
            a = 0x25C00000 + m.r16(a + 2) * 8 if (c >> 12) & 3 == 1 else a + 32
    ok = True
    m = mk(); S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    ra, rb = walk(m, H.LA), walk(m, H.LB)
    tex_ok = bytes(m.r8(H.TEX + i) for i in range(H.TEXN)) == b[:H.TEXN]
    own = [m.r16(H.OWN + 2 * i) for i in range(8)]
    print('켜짐: A %s · B %s · 그림 %s · 우리 칸 %s · 다음 END %04X' % (ra[1], rb[1], tex_ok, ' '.join('%04X' % x for x in own), m.r16(H.OWN + 32)))
    ok &= ra[1] == rb[1] == 'OURS' and tex_ok and m.r16(H.OWN + 32) == 0x8000
    S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})        # 두 번째 프레임 — 그대로
    ok &= walk(m, H.LA)[1] == walk(m, H.LB)[1] == 'OURS'
    m.w32(0x0608B348 + 0x34, 5)                                       # 재생 끝 → 꺼짐
    S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    ra, rb = walk(m, H.LA), walk(m, H.LB); print('꺼짐: A %s · B %s' % (ra[1], rb[1])); ok &= ra[1] == rb[1] == 'END'
    m = mk(); m.w32(0x0608B348 + 8, 0x1234)                           # 다른 조각 → 안 켜짐
    S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    ra, rb = walk(m, H.LA), walk(m, H.LB); print('다른 조각: A %s · B %s' % (ra[1], rb[1])); ok &= ra[1] == rb[1] == 'END'
    print('결과', '통과' if ok else '실패')
    return ok


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tex, px = render(LINES)
    pal = np.array([(40, 40, 60), (0, 0, 0), (255, 255, 255)], np.uint8)
    Image.fromarray(pal[px]).resize((px.shape[1] * 4, px.shape[0] * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'poc_sub.png'))
    kl, k4 = key(); print('열쇠 길이 0x%X · +0x%X = %08X' % (kl, H.keyoff(kl), k4))
    b, lab = H.blob(tex, kl, k4); print('묶음 %d B (%08X‥%08X) · 진입 %08X' % (len(b), H.AREA, H.AREA + len(b), lab['vbi']))
    assert test(b, lab)
    if '--write' in sys.argv:
        import iso
        d0 = disc.read('/0.BIN'); n0 = H.patch_0bin(d0, b, lab)
        iso.patch(OUT, 1, {'/0.BIN': n0})
        import hashlib; print('md5', hashlib.md5(open(OUT, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
