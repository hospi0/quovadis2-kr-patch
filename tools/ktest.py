# -*- coding: utf-8 -*-
r"""가타카나→한글 8×8 훅(khook) 흉내기 검산(2026-10-11).
  스테이트 RAM 에 «바뀐 0.BIN 바이트 + RUN 이미지»를 얹고 원래 게임 그리기 함수를 그대로 돌린다(0x0603F7B4 = 스프라이트 등록만 흉내).
  확인: 한글 음절 → 캐시 칸 텍스처 · 그 칸 VRAM 화소 = 우리 글꼴 · 글자 간격 8/9 · ASCII 만 있는 문자열은 그대로 · LRU · 무기·이름 전부.
  python tools/ktest.py
"""
import importlib.util, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, state, han8, khook as K
_sp = importlib.util.spec_from_file_location('sim', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2sim.py')
S = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(S)
L = 0x06004000
STR = 0x060FEC00


class Env:
    def __init__(s, st, d0, d1, img):
        m0 = state.ram(os.path.join(ROOT, 'my files', '할일', st))
        s.m = m = S.Mem(); m.add(0x06000000, 0x100000, m0['H']); m.add(0x00200000, 0x100000, m0['L']); m.add(0x05C00000, 0x80000, m0['V1'])
        for i in range(len(d0)):
            if d0[i] != d1[i]: m.w8(L + i, d1[i])
        for i, v in enumerate(img): m.w8(K.KBASE + i, v)

    def draw(s, f, b):
        m = s.m
        for i, c in enumerate(b + b'\0'): m.w8(STR + i, c)
        log = []
        def spr(r, mm): log.append((r[4] & 0xFFFF, mm.r32(r[15] + 4) & 0xFFFF)); r[0] = 0
        r, n = S.run(m, f, regs=[0, 0, 0, 0, STR, 10, 20, 0], calls={0x0603F7B4: spr, 0x0603FB10: lambda r, mm: None})
        return log

    def tex_px(s, tex):
        m = s.m; e = m.r32(0x060AAA44) + tex * 10; cg = m.r16(e); hv = m.r16(e + 2)
        w = (hv >> 8 & 0x3F) * 8; h = hv & 0xFF; a = 0x25C00000 + cg * 8
        return hv, [[(m.r8(a + (y * w + x) // 2) >> (4 if x % 2 == 0 else 0)) & 15 for x in range(w)] for y in range(h)]


def boot_check(d0):
    """부팅 init(보관 자리 RLE → RUN) 뒤 0x060FD000‥ 이 khook 이미지와 같은지 · 자막 RUN 도 그대로인지"""
    import mhook as M, hook as H
    dk, kimg, _ = K.build(d0)
    img0 = M.run_image()[0]
    parts, lab, _ = M.blob(extra=(K.KBASE, kimg)); b = M.patch_0bin(dk, parts, lab)
    m = S.Mem(); m.add(0x06000000, 0x100000)
    for i, v in enumerate(b): m.w8(L + i, v)
    for a in range(H.RUN, H.INIT_TOP): m.w8(a, 0xEE)
    S.run(m, lab['init'], calls={H.MAIN: lambda r, mm: None})
    got = bytes(m.r8(K.KBASE + i) for i in range(len(kimg)))
    sub = bytes(m.r8(H.RUN + i) for i in range(len(img0)))
    for fi, (e, si) in enumerate(K.FUNCS):
        kl = K.build(d0)[2]; at = e + (8 if e == K.F3 else K.nstub(e) - 4)
        assert struct.unpack_from('>I', b, at - L)[0] == kl['wrap%d' % fi]
        if e == K.F3: assert struct.unpack_from('>I', b, e + 20 - L)[0] == kl['remap']
    return got == kimg and sub == img0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d0 = disc.read('/0.BIN', 1); d1, img, lab = K.build(d0)
    rows, syl = K.table(); idx = {c: i for i, c in enumerate(syl)}
    ok = True
    def chk(c, msg):
        nonlocal ok
        if not c: ok = False; print('  ✗', msg)
    for st, fi in (('장비화면.state', 0), ('장비화면.state', 1), ('미션메뉴.state2', 0), ('미션메뉴.state2', 3), ('미션메뉴.state2', 4)):
        env = Env(st, d0, d1, img); f, si = K.FUNCS[fi]; base = K.SETS[si][0]
        # ① ASCII 만: 원본 함수와 같은 결과
        lg = env.draw(f, b'LB22 AP'); chk(len(lg) == (7 if si == 3 else 6), 'ASCII 글자 수 %d' % len(lg))
        # ② 이름·무기 전부(ASCII + 한글 섞임)
        nkr = 0
        for r in rows:
            t = r['ko']; lg = env.draw(f, K.enc(t, idx))
            ks = [c for c in t if c != ' ' or si == 3]       # F4·F5 는 띄어쓰기도 글자로 그림
            chk(len(lg) == len(ks), '%s 글자 수 %d≠%d' % (t, len(lg), len(ks)))
            for (tex, x), c in zip(lg, ks):
                if not ('가' <= c <= '힣'): continue
                nkr += 1
                g = tex - base; chk(g in K.SETS[si][2], '%s %s 텍스처 0x%X 가 캐시 칸 아님' % (t, c, tex))
                hv, px = env.tex_px(tex)
                if hv == 0x0108:
                    want, _ = han8.glyph(c)
                    chk(px == [[1 if v else 0 for v in row] for row in want], '%s %s 화소 다름' % (t, c))
            nxt_sp = [t[i + 1:i + 2] == ' ' for i, c in enumerate(t) if c != ' ' or si == 3]
            for (t0, x0), (t1, x1), c, sp in zip(lg, lg[1:], ks, nxt_sp):
                if '가' <= c <= '힣' and K.SETS[si][1] and not sp:
                    chk(x1 - x0 == han8.glyph(c)[1], '%s %s 간격 %d' % (t, c, x1 - x0))
        # ③ LRU: 한 문자열 안에서는 칸이 겹치지 않음 · 방금 쓴 음절이 다음 문자열에서 안 밀림
        many = ''.join(syl[:12]); lg = env.draw(f, K.enc(many, idx))
        chk(len({t for t, x in lg}) == 12, 'LRU 한 문자열 안 겹침')
        print('%s F%d(0x%08X): 한글 글자 %d · %s' % (st, fi + 1, f, nkr, '통과' if ok else '실패'))
    # ⑤ F3(메뉴 16×16): 고친 IFF 를 VRAM 에 올린 뒤 이름·기타 문구 → 텍스처 = iffkr.tex16(음절) · 화소 = 갈무리 글자 · 간격 ADV16
    import iffkr
    for st, vbase in (('장비화면.state', 0x33000), ('미션결과4.state3', 0x71000)):
        env = Env(st, d0, d1, img); iff = iffkr.build(disc.read('/S1/IFF.Z', 1), syl)
        for i, v in enumerate(iff): env.m.w8(0x25C00000 + vbase + i, v)
        n16 = 0
        for r in rows:
            if r['kind'] == 'weapon': continue
            t = r['ko']; lg = [g for g in env.draw(K.F3, K.enc(t, idx)) if g[0] != 0x4A3]   # 가나 뒤 띄어쓰기 = 빈 16×16 글자(0x4A3)
            ks = [c for c in t if c != ' ']
            chk(len(lg) == len(ks), 'F3 %s 글자 수' % t)
            for (tex, x), c in zip(lg, ks):
                if '가' <= c <= '힣':
                    n16 += 1; chk(tex == iffkr.tex16(idx[c]), 'F3 %s %s 텍스처 0x%X' % (t, c, tex))
                    hv, px = env.tex_px(tex); chk(hv == 0x0210 and px == iffkr.glyph16(c), 'F3 %s %s 화소' % (t, c))
            nxt_sp = [t[i + 1:i + 2] == ' ' for i, c in enumerate(t) if c != ' ']
            for (t0, x0), (t1, x1), c, sp in zip(lg, lg[1:], ks, nxt_sp):
                if '가' <= c <= '힣' and not sp: chk(x1 - x0 == iffkr.ADV16, 'F3 %s %s 간격 %d' % (t, c, x1 - x0))
        lg = env.draw(K.F3, b'LB22 AP'); chk(len(lg) == 7, 'F3 ASCII')                  # 원본 F3 도 띄어쓰기를 0x4A3 으로 그림
        print('%s F3(16×16): 한글 글자 %d · %s' % (st, n16, '통과' if ok else '실패'))
    # ④ 넓은 음절 수: 146 음절을 차례로 → 55칸 돌려 쓰기 뒤에도 마지막 55개는 그대로 남아야
    env = Env('장비화면.state', d0, d1, img); f = K.FUNCS[0][0]
    for c in syl: env.draw(f, K.enc(c, idx))
    sl = [env.m.r8(K.SLOTS + i) for i in range(K.NS)]
    chk(sorted(x - 1 for x in sl) == sorted(range(len(syl) - K.NS, len(syl))), 'LRU 마지막 55개')
    bc = boot_check(d0); chk(bc, '부팅 init 풀기')
    print('부팅 init 풀기', '통과' if bc else '실패')
    print('전체', '통과' if ok else '실패')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
