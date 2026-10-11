# -*- coding: utf-8 -*-
r"""미션 자막 본판(mhook) 흉내기 검산(2026-10-11).
  부팅 init → vload(LoadFile 흉내: 디스크 파일을 그 주소에 복사, 경로 기록) → VBI(조각·진행마다 그림·자리·크기) → 끝/없는 조각/깨진 버퍼.
  python tools/mtest.py
"""
import importlib.util, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, vbank, hook as H, mhook as M, poc, state, ksub

_sp = importlib.util.spec_from_file_location('sim', r'C:\claude\project\gundam-sabakareshi-kr-patch\tools\sh2sim.py')
S = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(S)


def tex4(px):
    f = px.ravel(); return bytes(((f[0::2] << 4) | f[1::2]).tolist())


def walk(m, a):
    seen = set()
    while a not in seen:
        seen.add(a); c = m.r16(a)
        if c & 0x8000: return 'END'
        if c == 0x5000 and m.r16(a + 2) == H.OWNL: return 'OURS'
        a = 0x25C00000 + m.r16(a + 2) * 8 if (c >> 12) & 3 == 1 else a + 32
    return 'LOOP'


def main(extra=None):
    sys.stdout.reconfigure(encoding='utf-8')
    parts, lab, img = M.blob()
    print('RUN 코드 %08X‥%08X · 임시 끝 %08X · vbi %08X · vload %08X · 보관 %s' % (M.RUN, M.RUN + len(img), lab['runend'], lab['vbi'], lab['vload'], ' '.join('%08X+%d' % (a, len(x)) for a, x in parts.items())))
    ks = extra or ksub.build(disks=(1,))[1]
    m0 = state.ram(poc.STATE)
    m = S.Mem(); m.add(0x06000000, 0x100000, m0['H']); m.add(0x00200000, 0x100000, m0['L']); m.add(0x05C00000, 0x80000, m0['V1'])
    hb = m._f(0x06000000)[0]
    hb[H.RUN - 0x06000000:H.RUN_END - 0x06000000] = bytes(H.RUN_END - H.RUN)
    for a, x in parts.items(): hb[a - 0x06000000:a - 0x06000000 + len(x)] = x
    S.run(m, lab['init'], calls={H.MAIN: lambda r, mm: None})
    for a, x in parts.items(): hb[a - 0x06000000:a - 0x06000000 + len(x)] = bytes(len(x))
    ok = bytes(m.r8(M.RUN + i) for i in range(len(img))) == img
    print('부팅 init 풀기', ok)
    loads = []
    def lf(r, mm):
        p = b''
        a = r[4]
        while mm.r8(a): p += bytes([mm.r8(a)]); a += 1
        p = p.decode(); loads.append((p, r[5]))
        dd, fn = p.split('/')
        data = ks[dd][fn] if fn.startswith('K') else disc.read('/' + p, 1)
        for i in range(0, len(data)): mm.w8(r[5] + i, data[i])
        r[0] = 0x0004 if fn.startswith('K') else 0x0002
    polls = []
    def srv(r, mm): pass
    def poll(r, mm):
        polls.append(r[4]); r[0] = 0 if len(polls) % 3 == 0 else r[4]       # 세 번째에 완료(비동기 흉내)
    def vload(path, slot):
        a = 0x060FF800
        for i, c in enumerate(path.encode() + b'\0'): m.w8(a + i, c)
        r, _ = S.run(m, lab['vload'], regs=[0, 0, 0, 0, a, slot], calls={M.LOADFILE: lf, M.SERVER: srv, M.POLL: poll})
        return r[0]
    def mainsrv():
        S.run(m, lab['srv'], regs=[0, 0, 0, 0, 0x06089830], calls={M.SERVER: srv_, M.POLL: poll})
    srvn = []
    def srv_(r, mm): srvn.append(1)
    loads.clear(); polls.clear()
    rv = vload('WDE00/VE013.B', 0x20250000)
    pend0 = m.r16(M.PEND)
    for _ in range(5): mainsrv()
    r1 = rv == 0x0002 and m.r16(M.VAR + 12) == 4 and pend0 == 4 and m.r16(M.PEND) == 0 and m.r16(M.VAR + 14) == 0 and loads == [('WDE00/VE013.B', 0x20250000), ('WDE00/KE01.B', M.BUF_A)]
    print('  비동기: vload 직후 대기 비트 %X → 메인 루프 srv 5번 뒤 %X · 폴링 %d번 · 서버 %d번' % (pend0, m.r16(M.PEND), len(polls), len(srvn)))
    loads.clear(); polls.clear(); vload('WDE00/VE012.B', 0x20270000)
    pend1 = m.r16(M.PEND)
    loads.clear(); polls.clear(); vload('WDE00/VE012.B', 0x20270000)              # 앞 요청 안 끝난 채 다음 vload → 그 자리에서 마저 기다림
    r2 = pend1 == 4 and loads == [('WDE00/VE012.B', 0x20270000), ('WDE00/KE01.B', M.BUF_B)] and len(polls) >= 1
    for _ in range(5): mainsrv()
    r2 &= m.r16(M.PEND) == 0
    loads.clear(); vload('WDE00/AE0D0.Z', 0x20270000)
    r3 = loads == [('WDE00/AE0D0.Z', 0x20270000)]
    print('vload: 반환값·짝 경로·칸 A %s · 칸 B %s · V 아닌 파일 건너뜀 %s' % (r1, r2, r3)); ok &= r1 and r2 and r3
    HB0 = 0x0608B348; HB = HB0 + M.HSTEP; CUR = 0x00240000; CUR2 = 0x00230000          # ★대사는 1번 핸들
    def vbi(name, ci, prog, side):
        d = disc.read(name, 1); o, ln, v = vbank.clips(d)[ci]
        k4 = struct.unpack_from('>I', d, o + H.keyoff(ln))[0]
        m.w32(HB0 + 0x34, 5); m.w32(HB0 + 4, 0x20000000 | CUR2); m.w32(HB0 + 8, 13216)   # 0번 핸들 = 효과음(끝남)
        m.w32(HB + 0x34, 4); m.w32(HB + 4, 0x20000000 | CUR); m.w32(HB + 8, ln); m.w32(HB + 0x70, prog)
        m.w32(CUR + H.keyoff(ln), k4)
        m.w8(0x060A575B, 0x00 if side == '위' else 0xFF); m.w8(0x060A56D7, 0xFF if side == '위' else 0x00)
        r, n = S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
        return n
    clips, segs = ksub.index(); tr = ksub.translations()
    md5of = {(n, c): m for d, n, c, m, ln in clips}
    for name, ci, _, side in poc.LINES[1:]:
        pp = ksub.pages_for(md5of[(name, ci)], segs, tr, {})               # 실제 번역의 첫 쪽(진행 0x100)
        lines = pp[0][1]
        px = poc.render(lines)
        n = vbi(name, ci, 0x100, side)
        t = tex4(px); got = bytes(m.r8(H.TEX + i) for i in range(len(t)))
        size = m.r16(H.OWN + 10); xy = (m.r16(H.OWN + 12), m.r16(H.OWN + 14))
        want = (H.XT, H.YT) if side == '위' else (H.X, H.Y)
        r = walk(m, H.LA) == walk(m, H.LB) == 'OURS' and got == t and size == (H.W8 << 8 | px.shape[0]) and xy == want
        n2 = vbi(name, ci, 0x200, side)
        print('%s#%d %s: 그림 %s · 크기 %04X · 자리 %s · 명령 %d(같은 쪽 다시 %d) → %s' % (name[7:], ci, side, got == t, size, xy, n, n2, '통과' if r else '실패'))
        ok &= r
    # 끝·없는 조각
    m.w32(HB + 0x34, 5); S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    r = walk(m, H.LA) == walk(m, H.LB) == 'END'; print('재생 끝 → END', r); ok &= r
    m.w32(HB + 0x34, 4); m.w32(HB + 8, 0x1234); S.run(m, lab['vbi'], calls={H.ORIG: lambda r, mm: None})
    r = walk(m, H.LA) == walk(m, H.LB) == 'END'; print('표에 없는 조각 → END', r); ok &= r
    # 깨진 버퍼(자료 한 바이트 바꿈) → 합 틀림 → 안 그림
    nm, ci, lines, side = poc.LINES[3]
    for BUF in (M.BUF_A, M.BUF_B):                                      # 두 칸이 같은 묶음일 수 있어 둘 다 깨뜨림
        for e in range(m.r32(BUF + 4)):
            off = m.r16(BUF + 8 + 16 * e + 8); m.w8(BUF + off + 3, m.r8(BUF + off + 3) ^ 0x10)
    m.w32(M.VAR + 4, 0); vbi(nm, ci, 0x100, side)
    r = walk(m, H.LA) == walk(m, H.LB) == 'END'; print('깨진 자료(합 틀림) → END', r); ok &= r
    # 여러 쪽: 가짜 짝 파일 — 같은 조각에 쪽 3개(0, 0x2000, 0x5000 바이트)
    d = disc.read('/WDE00/VE012.B', 1); o, ln, v = vbank.clips(d)[0]; k4 = struct.unpack_from('>I', d, o + H.keyoff(ln))[0]
    pg = [['첫 쪽'], ['둘째 쪽', '두 줄'], ['셋째 쪽', '세 줄', '셋']]
    kb = M.kfile([(ln, k4, f, poc.render(x)) for f, x in zip((0, 0x2000, 0x5000), pg)])
    for i in range(len(kb)): m.w8(M.BUF_B + i, kb[i])
    m.w32(M.VAR + 4, 0)
    for prog, want in ((0x10, 0), (0x1FFF, 0), (0x2000, 1), (0x4FFF, 1), (0x5000, 2), (0x9000, 2)):
        vbi('/WDE00/VE012.B', 0, prog, '아래')
        px = poc.render(pg[want]); t = tex4(px); got = bytes(m.r8(H.TEX + i) for i in range(len(t)))
        r = got == t and m.r16(H.OWN + 10) == (H.W8 << 8 | px.shape[0])
        print('쪽 넘김 진행 %05X → %d쪽 %s' % (prog, want + 1, r)); ok &= r
    print('결과', '통과' if ok else '실패')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
