# -*- coding: utf-8 -*-
r"""자막 PoC 4차(2026-10-11) — 미션1 위·아래 번갈아 말하는 대사 4개 + 미션대사2 대사.
  python tools/poc.py            → 그림 미리보기 work/poc_sub.png + 흉내기 검산(부팅 init → 대사마다 VBI, 위/아래 자리)
  python tools/poc.py --write    → work/out/…(Disc 1) (Track 1).bin (0.BIN 만 제자리)
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, vbank, hook as H, state

FONT = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Condensed.ttf'
# (V 파일, 조각, 줄들, 화자 쪽) — 부호 뒤 공백 없음(전프로젝트 규칙)
LINES = [
    ('/WDE00/VE001.B', 0, ['오반,화면 위 검은 차량이', '디온이야.지하도로 대통령이', '탈출할 때까지 시간을 벌어.'], '아래'),
    ('/WDE00/VE012.B', 0, ['네리입니다.이 부대에 거둬진 지', '10년이지만,싸워 본 적은', '없어요.잘 부탁드립니다.'], '아래'),
    ('/WDE00/VE013.B', 0, ['악운도 오늘로 끝이군.', '이런 난민 출신 천한 여자랑', '한편이라니.'], '위'),
    ('/WDE00/VE013.B', 1, ['죄,죄송해요.'], '아래'),
    ('/WDE00/VE013.B', 2, ['죄송하다고 끝나면', '전쟁 따윈 안 일어나.'], '위'),
]
STATE = os.path.join(ROOT, 'my files', '할일', '미션대사2.state3')
OUT = os.path.join(ROOT, 'work', 'out', 'QuoVadis 2 - Wakusei Kyoushuu Ovan Rei (Japan) (Disc 1) (Track 1).bin')


def render(lines):
    """160×(13n+2): 0 투명 · 1 검정 테두리 · 2 흰 글자(갈무리11 좁은꼴 비트맵 그대로, 줄 간격 13, 가운데)"""
    w, h = H.W8 * 8, 13 * len(lines) + 2
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
    return np.where(g, 2, np.where(b, 1, 0)).astype(np.uint8)


def key(name, ci):
    d = disc.read(name); o, ln, v = vbank.clips(d)[ci]
    return ln, struct.unpack_from('>I', d, o + H.keyoff(ln))[0]


def tex4(px):
    f = px.ravel(); return bytes(((f[0::2] << 4) | f[1::2]).tolist())


def test(parts, lab, ents):
    import importlib.util
    sp = importlib.util.spec_from_file_location('sim', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2sim.py')
    S = importlib.util.module_from_spec(sp); sp.loader.exec_module(S)
    m0 = state.ram(STATE)
    def mk():
        m = S.Mem(); m.add(0x06000000, 0x100000, m0['H']); m.add(0x00200000, 0x100000, m0['L']); m.add(0x05C00000, 0x80000, m0['V1'])
        hb = m._f(0x06000000)[0]
        hb[H.RUN - 0x06000000:H.RUN_END - 0x06000000] = bytes(H.RUN_END - H.RUN)
        for a, x in parts.items(): hb[a - 0x06000000:a - 0x06000000 + len(x)] = x
        S.run(m, lab['init'], calls={H.MAIN: lambda r, mm: None})
        for a, x in parts.items(): hb[a - 0x06000000:a - 0x06000000 + len(x)] = bytes(len(x))
        return m
    def walk(m, a):
        seen = set()
        while a not in seen:
            seen.add(a); c = m.r16(a)
            if c & 0x8000: return 'END'
            if c == 0x5000 and m.r16(a + 2) == H.OWNL: return 'OURS'
            a = 0x25C00000 + m.r16(a + 2) * 8 if (c >> 12) & 3 == 1 else a + 32
    ok = True
    m = mk()
    CUR = 0x00240000                                                  # 흉내용 조각 자리(하위 RAM)
    for (name, ci, lines, side), (ln, k4, px) in zip(LINES, ents):
        m.w32(0x0608B348 + 0x34, 4); m.w32(0x0608B348 + 4, 0x20000000 | CUR); m.w32(0x0608B348 + 8, ln)
        m.w32(CUR + H.keyoff(ln), k4)
        m.w8(0x060A575B, 0x00 if side == '위' else 0xFF); m.w8(0x060A56D7, 0xFF if side == '위' else 0x00)
        S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
        t = tex4(px); got = bytes(m.r8(H.TEX + i) for i in range(len(t)))
        size = m.r16(H.OWN + 10); xy = (m.r16(H.OWN + 12), m.r16(H.OWN + 14))
        want_xy = (H.XT, H.YT) if side == '위' else (H.X, H.Y)
        r = walk(m, H.LA) == walk(m, H.LB) == 'OURS' and got == t and size == (H.W8 << 8 | px.shape[0]) and xy == want_xy
        print('%s#%d %s: 그림 %s · 크기 %04X · 자리 %s → %s' % (name[7:], ci, side, got == t, size, xy, '통과' if r else '실패'))
        ok &= r
    m.w32(0x0608B348 + 0x34, 5); S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    r = walk(m, H.LA) == walk(m, H.LB) == 'END'; print('재생 끝 → END', r); ok &= r
    m.w32(0x0608B348 + 0x34, 4); m.w32(0x0608B348 + 8, 0x1234); S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    r = walk(m, H.LA) == walk(m, H.LB) == 'END'; print('표에 없는 조각 → END', r); ok &= r
    print('결과', '통과' if ok else '실패')
    return ok


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ents = []
    for name, ci, lines, side in LINES:
        px = render(lines); ln, k4 = key(name, ci); ents.append((ln, k4, px))
    pal = np.array([(40, 40, 60), (0, 0, 0), (255, 255, 255)], np.uint8)
    img = np.vstack([np.vstack([p, np.zeros((4, p.shape[1]), np.uint8)]) for _, _, p in ents])
    Image.fromarray(pal[img]).resize((img.shape[1] * 3, img.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'poc_sub.png'))
    parts, lab, run = H.blob(ents)
    print('RUN %d B (%08X‥%08X) · 보관' % (len(run), H.RUN, H.RUN + len(run)), ' · '.join('%08X+%d B' % (a, len(x)) for a, x in parts.items()), '· 진입 %08X · init %08X' % (lab['vbi'], lab['init']))
    assert test(parts, lab, ents)
    if '--write' in sys.argv:
        import iso, hashlib
        n0 = H.patch_0bin(disc.read('/0.BIN'), parts, lab)
        iso.patch(OUT, 1, {'/0.BIN': n0})
        print('md5', hashlib.md5(open(OUT, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
