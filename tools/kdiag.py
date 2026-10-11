# -*- coding: utf-8 -*-
r"""미션 음성 자막 실기 진단(2026-10-11) — 스테이트에서 지금 조각·짝 파일 버퍼·진단 값.
  python tools/kdiag.py 스테이트
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import state, hook as H, mhook as M, ksub

HB = 0x0608B348


def main(path):
    sys.stdout.reconfigure(encoding='utf-8')
    m = state.ram(path); hb = m['H']; lo = m['L']
    def r(a, n):
        if a & 0x0FF00000 == 0x06000000: return hb[(a & 0xFFFFF):(a & 0xFFFFF) + n]
        return lo[(a & 0xFFFFF):(a & 0xFFFFF) + n]
    u32 = lambda a: struct.unpack('>I', r(a, 4))[0]
    u16 = lambda a: struct.unpack('>H', r(a, 2))[0]
    st, cur, ln, prog = u32(HB + 0x34), u32(HB + 4), u32(HB + 8), u32(HB + 0x70)
    k4 = u32((cur & 0x0FFFFFFF) + H.keyoff(ln)) if cur else 0
    print('핸들 상태 %d · 조각 주소 %08X · 길이 %d(%.2f초) · 진행 %X(%.2f초) · 열쇠 %08X' % (st, cur, ln, ln / 11025, prog, prog / 11025, k4))
    print('VAR 붙음 %08X · 지금 항목 %08X · 높이 %d · LoadFile 반환 %04X · 끝 상태 %04X' % (u32(M.VAR), u32(M.VAR + 4), u32(M.VAR + 8), u16(M.VAR + 12), u16(M.VAR + 14)))
    kp = bytes(r(M.KPATH, 28)).split(b'\0')[0]
    print('마지막 짝 경로', kp)
    for nm, B in (('A', M.BUF_A), ('B', M.BUF_B)):
        mg, n = u32(B), u32(B + 4)
        hit = [e for e in range(min(n, 2000)) if u32(B + 8 + 16 * e) == ln and u32(B + 12 + 16 * e) == k4] if mg == M.MAGIC else []
        print('버퍼 %s: 마법 %08X · 항목 %d · 지금 조각 있음 %s' % (nm, mg, n, hit))
    clips, segs = ksub.index(); tr = ksub.translations()
    import disc, vbank
    found = [(d, n, c, md) for d, n, c, md, l in clips if l == ln]
    for d, n, c, md in found:
        dat = disc.read(n, d); o, l2, v = vbank.clips(dat)[c]
        if struct.unpack_from('>I', dat, o + H.keyoff(ln))[0] != k4: continue
        print('조각 = 장 %d %s #%d' % (d, n, c))
        for i, s, e in segs.get(md, []):
            print('   %s %.2f‥%.2f 번역 %s' % (i, s, e, tr.get(i, '(없음)')))


if __name__ == '__main__':
    main(sys.argv[1])
